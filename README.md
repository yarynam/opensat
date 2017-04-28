![alt tag](http://image.prntscr.com/image/cd1b31fb589448babe424761c3b35627.png)


# Opensat

Handy tool for downloading, searching and processing Landsat 8 and Sentinel data. Beta version.


## == DONE ==
1.Create opensat directories within user's home directories

2.Check for server errors

3.Download all Landsat bands by scene ID
```
$ python opensat.py download -s LC80020252016253LGN00
```

4.Download selected Landsat bands by scene ID
```
$ python opensat.py download -s LC80020252016253LGN00 -b 2,3,4
```

5.Download all Sentinel bands by scene ID
```
$ python opensat.py download -s S2A_tile_20160823_19TDJ_0
```

6.Download selected Sentinel bands by scene ID
```
$ python opensat.py download -s S2A_tile_20160823_19TDJ_0 -b 1,3,10
```

7.Search/download all scenes for Landsat path
```
$ python opensat.py search -l 13,32
```

8.Search/download all scenes for Landsat path with particular cloud coverage
```
$ python opensat.py search -l 13,32 -c 5
```

9.Download all scenes for Landsat path with particular date and cloud coverage
```
$ python opensat.py search -l 13,32 -d 2016-04-12,2016-08-10 -c 5
```

10.Search/download all scenes for Sentinal path
```
$ python opensat.py search -l 18TXL
```

11.Search/download all scenes for Sentinal path with particular cloud coverage
```
$ python opensat.py search -l 18TWL -c 10
```

12.Download all scenes for Sentinel path with particular date and cloud coverage
```
$ python opensat.py search -l 18TWL -d 2016-04-12,2016-08-10  -c 5
```

13.Stack bands after downloading (example with true color)
```
$ python opensat.py download -s LC80020252016253LGN00 -b 2,3,4 -p 432
```

14.Stack bands and run pansharpening after downloading (example with true color for Landsat only)
```
$ python opensat.py download -s LC80020252016253LGN00 -b 2,3,4,8 -p 4328
```

14.Mask processed images after downloading with a shapefile (needs a path to a mask file; mask file should have the same projection)
```
$ python opensat.py download -s LC80020252016253LGN00 -b 2,3,4 -p 4328 -m mask_folder/mask.shp
```
15.Check if file already exists

16.Fix socket.error: [Errno 60] Operation timed out

17.Check for non-existing file




## == T0-DO ==

1.Add NDVI calculations

2.Generate opensat_info.json --> metafile with all operations.

3.Test and restructure. Create parent class for Landsat and Sentinal

4.Package as a command line tool. Follow this tutorial https://python-packaging.readthedocs.io/en/latest/
