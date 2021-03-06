import os
import errno
import shutil
import time
import warnings
import subprocess
import numpy as np

from scipy.ndimage.filters import gaussian_filter, median_filter, maximum_filter, minimum_filter, uniform_filter
from scipy.ndimage import label, grey_closing
from skimage.morphology import convex_hull_image
from sklearn.decomposition import PCA
from skimage.filters import threshold_otsu, rank

from .util import get_bbox, convex_hull_image_3d, fill_holes3d
from .util import umtRead, umtWrite
from .util import get_first_crossing_time

def renal_segment_v4(recon, temp_res, spacing, root_path, threshold_multiplier=1):
    # Based on Grabcut_Renal_Dev_v16
    # recon     : 4D dataset [x,y,z,t]
    # temp_res  : temporal resolution in sec
    # spacing   : spatial resolution in mm [x,y,z]

    cleanup_enabled = True

    GC_BGD = 0
    GC_FGD = 1
    GC_PR_BGD = 2
    GC_PR_FGD = 3

    nx, ny, nz, nt = recon.shape

    if issubclass(recon.dtype.type, np.integer):
        recon -= np.amin(recon)
        # Use look up table
        lut = np.arange(np.amax(recon)+1).astype(np.float)
        lut = (lut/np.amax(lut)*255).astype(np.uint8)
        recon = lut[recon]
    else:
        recon -= np.amin(recon)
        recon /= np.amax(recon)
        recon = (recon*255).astype(np.uint8)

    ## Find medulla clusters ##
    sig = recon.reshape(-1, nt)
    mean_sig = np.mean(sig, axis=0)

    mean_sig = gaussian_filter(mean_sig, 10/temp_res)  # Filter to reduce temporal noise

    t_5p = get_first_crossing_time(mean_sig, 0.10)[0]
    t_5p = np.floor(t_5p).astype(np.int)
    t_start = max(t_5p, 0)

    t_30 = min(t_start+np.ceil(30/temp_res).astype(np.int), nt-1)
    t_45 = min(t_start+np.ceil(45/temp_res).astype(np.int), nt-1)
    t_60 = min(t_start+np.ceil(60/temp_res).astype(np.int), nt-1)
    t_90 = min(t_start+np.ceil(90/temp_res).astype(np.int), nt-1)
    t_120 = min(t_start+np.ceil(120/temp_res).astype(np.int), nt-1)
    t_180 = min(t_start+np.ceil(180/temp_res).astype(np.int), nt-1)
    t_240 = min(t_start+np.ceil(240/temp_res).astype(np.int), nt-1)

    # Penalize voxels with high initial intensity
    start_score = recon[:,:,:,t_start].astype(np.float).copy()
    start_score = gaussian_filter(start_score, 2/spacing)
    start_score -= np.amin(start_score)
    start_score /= np.amax(start_score)
    start_score = 1 - start_score

    # Penalize voxels where motion is dominant
    y = sig[:,t_60:t_120].astype(np.float).T
    x = np.arange(y.shape[0])
    Z = np.polyfit(x, y, 2)
    X = np.vstack((x**2, x**1, x**0))
    y_fit = np.dot(Z.T, X)
    y_res = y.T-y_fit
    y_res_std = np.std(y_res, axis=1)
    y_res_std3d = y_res_std.reshape(nx, ny, nz)
    motion_score = y_res_std3d.copy()
    motion_score = gaussian_filter(motion_score, 2/spacing)
    motion_score -= np.amin(motion_score)
    motion_score /= np.amax(motion_score)
    motion_score = 1 - motion_score
    
    # Look at time to peak
    im_90p = get_first_crossing_time(recon[:,:,:,t_start:t_60], 0.90)
    im_90p[im_90p==0.0] = np.amax(im_90p)
    im_90p = gaussian_filter(im_90p, sigma=2/spacing)
    im_90p -= np.amin(im_90p)
    im_90p /= np.amax(im_90p)
    im_90p = 1 - im_90p
    nb_mm = 11 # Based on cortical thickness
    nb = np.ceil(nb_mm/spacing).astype(np.int)
    im_90p_filt = im_90p.copy()
    im_90p_filt = maximum_filter(im_90p_filt, nb)
    im_90p_filt = minimum_filter(im_90p_filt, nb)
    med_temp_score = im_90p_filt

    # Get images at predetermined time points
    recon_bl = gaussian_filter(recon.astype(np.float), np.hstack((0/spacing, 10/temp_res)))
    recon_start = recon_bl[:,:,:,t_start].astype(np.float)
    recon_30 = recon_bl[:,:,:,t_30].astype(np.float)
    recon_45 = recon_bl[:,:,:,t_45].astype(np.float)
    recon_60 = recon_bl[:,:,:,t_60].astype(np.float)
    recon_90 = recon_bl[:,:,:,t_90].astype(np.float)
    recon_120 = recon_bl[:,:,:,t_120].astype(np.float)
    recon_240 = recon_bl[:,:,:,t_240].astype(np.float)

    # Medulla Marker
    med_marker3_1 = (recon_60-recon_start)
    med_marker3_1[med_marker3_1 < 0] = 0
    med_marker3_1 = gaussian_filter(med_marker3_1, 2/spacing)
    med_marker3_1 -= np.amin(med_marker3_1)
    med_marker3_1 /= np.amax(med_marker3_1)

    med_marker3_2 = (recon_120 - recon_60)
    mask = med_marker3_2 > 0
    med_marker3_2[med_marker3_2 < 0] = 0
    med_marker3_2 = gaussian_filter(med_marker3_2, 2/spacing)
    med_marker3_2 -= np.amin(med_marker3_2)
    med_marker3_2 /= np.amax(med_marker3_2)

    med_marker3 = np.ones((nx, ny, nz), dtype=np.float)
    med_marker3 = med_marker3 * med_marker3_1
    med_marker3 = med_marker3 * med_marker3_2
    med_marker3 = med_marker3 * motion_score
    med_marker3 = med_marker3 * start_score
    med_marker3 = med_marker3 * med_temp_score
    med_marker3 = med_marker3/np.amax(med_marker3)

    med_marker3[med_marker3 < 0] = 0
    med_marker_filt3 = med_marker3*mask

    # If available calculate CS Marker
    if (t_180 < nt-1):
        # Look at time to peak
        cs_im_90 = get_first_crossing_time(recon[:,:,:,t_start:t_180], 0.90)
        cs_im_90 = gaussian_filter(cs_im_90, sigma=2/spacing)
        cs_im_90 -= np.amin(cs_im_90)
        cs_im_90 /= np.amax(cs_im_90)
        cs_temp_score = cs_im_90

        med_marker4_2 = (recon_240 - recon_120)
        mask = med_marker4_2 > 0
        med_marker4_2[med_marker4_2 < 0] = 0
        med_marker4_2 = gaussian_filter(med_marker4_2, 2/spacing)
        med_marker4_2 -= np.amin(med_marker4_2)
        med_marker4_2 /= np.amax(med_marker4_2)

        med_marker4 = np.ones((nx, ny, nz), dtype=np.float)
        med_marker4 = med_marker4 * med_marker4_2
        med_marker4 = med_marker4 * motion_score
        med_marker4 = med_marker4 * start_score
        med_marker4 = med_marker4 * cs_temp_score
        med_marker4 = med_marker4/np.amax(med_marker4)

        med_marker4[med_marker4 < 0] = 0
        med_marker_filt4 = med_marker4*mask

    # Combine medulla marker with cs marker if available
    if (t_180 < nt-1):
        med_marker5 = med_marker4/np.amax(med_marker4) + med_marker_filt3/np.amax(med_marker_filt3)
        med_marker_filt5 = med_marker_filt4/np.amax(med_marker_filt4) + med_marker_filt3/np.amax(med_marker_filt3)
    else:
        med_marker_filt5 = med_marker_filt3

    med_marker_im3d = med_marker_filt5.copy()
    med_marker_im3d -= np.amin(med_marker_im3d)
    med_marker_im3d /= np.amax(med_marker_im3d)
    med_marker_im3d = (255*med_marker_im3d).astype(np.uint8)

    med_cutoff_otsu = threshold_otsu(med_marker_im3d[med_marker_im3d>0].ravel())*threshold_multiplier

    # Connect nearby medulla regions
    nb_mm = 11 # Based on cortical thickness
    nb = np.ceil(nb_mm/spacing).astype(np.int)
    med_valid = med_marker_im3d.astype(np.float) > med_cutoff_otsu
    med_valid_max = maximum_filter(med_valid, nb)
    med_valid_label, num_labels = label(med_valid_max)
    med_valid_label[med_valid==0] = 0

    # Find the largest 4 clusters
    cluster_size = np.bincount(med_valid_label.ravel())
    cluster_size[0] = 0
    sorted_clusters = np.argsort(cluster_size)[::-1]
    largest_n = 4
    med_valid_largest = np.zeros_like(med_valid_label)
    for i in range(min(largest_n, sorted_clusters.shape[0])):
        cluster_id = sorted_clusters[i]
        if cluster_size[cluster_id] > 0:
            med_valid_largest[med_valid_label == cluster_id] = i+1

    ## GrabCut Section ##
    tic_cell = time.time()
    nb_mm = 25 # Based on cortical thickness (12.5 mm extension on all sides for max cort. thickness of 11mm)
    nb = np.ceil(nb_mm/spacing).astype(np.int)

    recon_min = np.amin(recon, axis=3, keepdims=True)
    recon_diff = gaussian_filter(recon - recon_min, np.hstack((0/spacing, 0/temp_res)))
        
    output3d = np.zeros((nx, ny, nz), dtype=np.int)
    output3d_bbox_list = []

    for cluster_id in np.unique(med_valid_largest[med_valid_largest > 0]):
        print("Cluster_id =", cluster_id)
        
        # Expand the mask by maximum cortical thickness to cover the whole kidney
        potential_mask = med_valid_largest == cluster_id
        potential_mask = maximum_filter(potential_mask, nb)
        
        # Generate the 3d convex hull
        potential_mask = convex_hull_image_3d(potential_mask)
        
        # Calculate the bounding box
        bbox = get_bbox(potential_mask)
        
        # Expand bbox to get more background
        scale = 1.5
        xyz_min, xyz_end = bbox
        xyz_len = xyz_end-xyz_min
        xyz_len_shift = np.round((scale-1)*xyz_len).astype(np.int)
        new_xyz_min = xyz_min - np.floor(xyz_len_shift/2).astype(np.int)
        new_xyz_min[new_xyz_min < 0] = 0
        new_xyz_len = xyz_len + xyz_len_shift
        new_xyz_max = new_xyz_min + new_xyz_len
        new_xyz_over = new_xyz_max - [nx,ny,nz]
        new_xyz_over[new_xyz_over < 0] = 0
        new_xyz_len = xyz_len + xyz_len_shift - new_xyz_over
        bbox = (new_xyz_min, new_xyz_min + new_xyz_len)
        
        bb_l, bb_h = bbox
        potential_mask_bbox = potential_mask[bb_l[0]:bb_h[0], bb_l[1]:bb_h[1], bb_l[2]:bb_h[2]]
        
        # Calculate PCA
        recon_diff_bbox = recon_diff[bb_l[0]:bb_h[0], bb_l[1]:bb_h[1], bb_l[2]:bb_h[2], :]
        nx_bb, ny_bb, nz_bb, nt_bb = recon_diff_bbox.shape
        pca = PCA(n_components=3)
        im3d_pca_bbox = pca.fit_transform(recon_diff_bbox.reshape(-1, recon_diff_bbox.shape[-1]).astype(np.float))
        im3d_pca_bbox = im3d_pca_bbox.reshape(nx_bb, ny_bb, nz_bb, -1)
        im3d_rgb_bbox = im3d_pca_bbox.copy()
        for ch in range(im3d_rgb_bbox.shape[3]):
            im3d_ch = im3d_rgb_bbox[:,:,:,ch]
            im3d_ch -= np.amin(im3d_ch)
            im3d_ch = im3d_ch/np.amax(im3d_ch)*255
            im3d_rgb_bbox[:,:,:,ch] = im3d_ch
        im3d_rgb_bbox = im3d_rgb_bbox.astype(np.uint8)

        # Perform GrabCut
        potential_mask3d_bbox = potential_mask_bbox
        img_gc = np.transpose(im3d_rgb_bbox, (2, 0, 1, 3))

        mask_gc = np.zeros(im3d_rgb_bbox.shape[:3], np.uint8)
        mask_gc[potential_mask3d_bbox > 0] = GC_PR_FGD
        mask_gc = np.transpose(mask_gc, (2, 0, 1))

        # Create a directory for temporary files
        buffer_directory = os.path.join(root_path, "Buffer")
        try:
            os.makedirs(buffer_directory)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

        input_filename = os.path.join(buffer_directory, "input.umt")
        mask_filename = os.path.join(buffer_directory, "mask.umt")
        output_filename = os.path.join(buffer_directory, "output.umt")

        umtWrite(input_filename, img_gc)
        umtWrite(mask_filename, mask_gc)
    
        program_path = os.path.join(root_path, "CppSource", "GrabCut3d", "run_grabcut3d")
        tic = time.time()
        ret_val = subprocess.call([program_path, input_filename, mask_filename, output_filename])
        assert ret_val == 0, 'GrabCut function failed!'
        print('Elapsed time:', time.time()-tic)
    
        output3d_bbox = umtRead(output_filename)
        output3d_bbox = np.transpose(output3d_bbox, (1, 2, 0)) == GC_PR_FGD
            
        output3d_bbox_list.append(output3d_bbox)
        output3d_slice = output3d[bb_l[0]:bb_h[0], bb_l[1]:bb_h[1], bb_l[2]:bb_h[2]]
        output3d_slice[output3d_bbox > 0] = output3d_bbox[output3d_bbox > 0]
    print('Cell_Time =', time.time()-tic_cell)

    # Remove temporary files
    shutil.rmtree(buffer_directory)

    ## Label the connected regions ##
    kidney_labels, n_labels = label(output3d)
    cluster_size = np.bincount(kidney_labels.ravel())

    # Eliminate anything below 25% of the largest region
    cluster_size[0] = 0
    cluster_size_cutoff = np.amax(cluster_size)*0.25
    cluster_size[cluster_size < cluster_size_cutoff] = 0
    cluster_id = 0
    for i in range(n_labels+1):
        if cluster_size[i] > 0:
            cluster_id += 1
            cluster_size[i] = cluster_id
    kidney_labels = cluster_size[kidney_labels]

    cluster_size = np.bincount(kidney_labels.ravel())

    ## 3D Cleanup ##
    if cleanup_enabled:
        # Fill holes in x, y, z slices for robustness
        # This will fill up the convex volume before erosion.
        output_filled = fill_holes3d(output3d)

        nb_mm = 3.2*2 # (2 x minimum cortical thickness)
        nb = np.floor(nb_mm/spacing).astype(np.int) # (floor to be conservative)
        nb[nb<3] = 3 # At least 1 voxel in each direction

        # Erode the output of the first pass
        # output3d_eroded = minimum_filter(output3d, nb)
        output3d_eroded = minimum_filter(output_filled, nb)
        output3d_opened = maximum_filter(output3d_eroded, nb+2)

        output3d_cleaned = output3d.copy()
        output3d_cleaned[output3d_opened > 0] = 0

        output3d_final2 = output3d.copy()
        output3d_final2[output3d_opened == 0] = 0

        kidney_labels, n_labels = label(output3d_final2)
        cluster_size = np.bincount(kidney_labels.ravel())

        # Eliminate anything below 25% of the largest region
        cluster_size[0] = 0
        cluster_size_cutoff = np.amax(cluster_size)*0.25
        cluster_size[cluster_size < cluster_size_cutoff] = 0
        cluster_id = 0
        for i in range(n_labels+1):
            if cluster_size[i] > 0:
                cluster_id += 1
                cluster_size[i] = cluster_id
        kidney_labels = cluster_size[kidney_labels]

        # Eliminate noisy regions
        sig = recon.reshape(-1, nt)
        kidney_labels_fixed = np.zeros_like(kidney_labels)
        valid_count = 0
        valid_sig = []
        invalid_sig = []
        for cluster_id in np.unique(kidney_labels[kidney_labels > 0]):
            cluster_mask = kidney_labels == cluster_id
            sig_mask = np.mean(sig[cluster_mask.ravel(), :], axis=0)
            t_50p = get_first_crossing_time(sig_mask.reshape(1, -1), 0.50)
            if t_50p < t_start or t_50p > t_30:
                print('Noise_detected!')
                invalid_sig.append(sig_mask)
                continue
            valid_sig.append(sig_mask)
            valid_count += 1
            kidney_labels_fixed[cluster_mask > 0] = valid_count
        kidney_labels = kidney_labels_fixed

    print('Segmentation completed.')
    return kidney_labels
