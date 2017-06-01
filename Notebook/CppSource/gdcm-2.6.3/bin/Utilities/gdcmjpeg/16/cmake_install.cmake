# Install script for directory: /Users/umityoruk/Documents/PythonDev/NewSegmentation/Notebook/CppSource/gdcm-2.6.3/Utilities/gdcmjpeg/16

# Set the install prefix
if(NOT DEFINED CMAKE_INSTALL_PREFIX)
  set(CMAKE_INSTALL_PREFIX "/usr/local")
endif()
string(REGEX REPLACE "/$" "" CMAKE_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}")

# Set the install configuration name.
if(NOT DEFINED CMAKE_INSTALL_CONFIG_NAME)
  if(BUILD_TYPE)
    string(REGEX REPLACE "^[^A-Za-z0-9_]+" ""
           CMAKE_INSTALL_CONFIG_NAME "${BUILD_TYPE}")
  else()
    set(CMAKE_INSTALL_CONFIG_NAME "")
  endif()
  message(STATUS "Install configuration: \"${CMAKE_INSTALL_CONFIG_NAME}\"")
endif()

# Set the component getting installed.
if(NOT CMAKE_INSTALL_COMPONENT)
  if(COMPONENT)
    message(STATUS "Install component: \"${COMPONENT}\"")
    set(CMAKE_INSTALL_COMPONENT "${COMPONENT}")
  else()
    set(CMAKE_INSTALL_COMPONENT)
  endif()
endif()

if(NOT CMAKE_INSTALL_COMPONENT OR "${CMAKE_INSTALL_COMPONENT}" STREQUAL "DebugDevel")
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib" TYPE STATIC_LIBRARY FILES "/Users/umityoruk/Documents/PythonDev/NewSegmentation/Notebook/CppSource/gdcm-2.6.3/bin/bin/libgdcmjpeg16.a")
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libgdcmjpeg16.a" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libgdcmjpeg16.a")
    execute_process(COMMAND "/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/ranlib" "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libgdcmjpeg16.a")
  endif()
endif()

if(NOT CMAKE_INSTALL_COMPONENT OR "${CMAKE_INSTALL_COMPONENT}" STREQUAL "DebugDevel")
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/gdcm-2.6/gdcmjpeg/16" TYPE FILE FILES
    "/Users/umityoruk/Documents/PythonDev/NewSegmentation/Notebook/CppSource/gdcm-2.6.3/bin/Utilities/gdcmjpeg/16/jconfig.h"
    "/Users/umityoruk/Documents/PythonDev/NewSegmentation/Notebook/CppSource/gdcm-2.6.3/bin/Utilities/gdcmjpeg/16/jerror.h"
    "/Users/umityoruk/Documents/PythonDev/NewSegmentation/Notebook/CppSource/gdcm-2.6.3/bin/Utilities/gdcmjpeg/16/jinclude.h"
    "/Users/umityoruk/Documents/PythonDev/NewSegmentation/Notebook/CppSource/gdcm-2.6.3/bin/Utilities/gdcmjpeg/16/jmorecfg.h"
    "/Users/umityoruk/Documents/PythonDev/NewSegmentation/Notebook/CppSource/gdcm-2.6.3/bin/Utilities/gdcmjpeg/16/jpegcmake.h"
    "/Users/umityoruk/Documents/PythonDev/NewSegmentation/Notebook/CppSource/gdcm-2.6.3/bin/Utilities/gdcmjpeg/16/jpeglib.h"
    "/Users/umityoruk/Documents/PythonDev/NewSegmentation/Notebook/CppSource/gdcm-2.6.3/bin/Utilities/gdcmjpeg/16/mangle_jpeg16bits.h"
    )
endif()
