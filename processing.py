import numpy
import json
import rasterio
from rasterio.warp import reproject, RESAMPLING, transform, transform_bounds

from skimage import transform as sktransform
from skimage.util import img_as_ubyte
from skimage.exposure import rescale_intensity
from polyline.codec import PolylineCodec
import warnings
import os

warnings.filterwarnings("ignore")



# Stacking bands is based on landsat-util code

class Processing(object):
    'Processing images'

    def __init__(self, scene, bands, satellite):
        self.bands_values = bands
        self.projection = {'init': 'epsg:3857'}
        self.dst_crs = {'init': u'epsg:3857'}
        self.satellite = satellite
        if self.satellite == "landsat":
            self.bands = [scene + "_B" + band + ".TIF" for band in bands]
        elif self.satellite == "sentinel":
            self.bands = ["B0" + band + ".jp2" for band in bands]
        self.scene = scene

        self.output_dir = os.path.expanduser("~") + "/openasat/" + satellite + "/" + self.scene + "/processed/"
        if not os.path.exists(self.output_dir):
            os.mkdir(os.path.expanduser(self.output_dir))

        self.bands_path = []
        self.scene_path = os.path.expanduser("~") + "/openasat/" + satellite + "/"  + self.scene + "/"
        for band in self.bands:
            self.bands_path.append(self.scene_path + band )

        self.output_file = self.output_dir + self.scene + "_" + self.bands_values + ".TIF"




    def _get_boundaries(self, src, shape):

            output = {'ul': {'x': [0, 0], 'y': [0, 0]},  # ul: upper left
                      'ur': {'x': [0, 0], 'y': [0, 0]},  # ur: upper right
                      'll': {'x': [0, 0], 'y': [0, 0]},  # ll: lower left
                      'lr': {'x': [0, 0], 'y': [0, 0]}}  # lr: lower right

            output['ul']['x'][0] = src['affine'][2]
            output['ul']['y'][0] = src['affine'][5]
            output['ur']['x'][0] = output['ul']['x'][0] + self.pixel * src['shape'][1]
            output['ur']['y'][0] = output['ul']['y'][0]
            output['ll']['x'][0] = output['ul']['x'][0]
            output['ll']['y'][0] = output['ul']['y'][0] - self.pixel * src['shape'][0]
            output['lr']['x'][0] = output['ul']['x'][0] + self.pixel * src['shape'][1]
            output['lr']['y'][0] = output['ul']['y'][0] - self.pixel * src['shape'][0]

            output['ul']['x'][1], output['ul']['y'][1] = transform(src['crs'], self.projection,
                                                                   [output['ul']['x'][0]],
                                                                   [output['ul']['y'][0]])

            output['ur']['x'][1], output['ur']['y'][1] = transform(src['crs'], self.projection,
                                                                   [output['ur']['x'][0]],
                                                                   [output['ur']['y'][0]])

            output['ll']['x'][1], output['ll']['y'][1] = transform(src['crs'], self.projection,
                                                                   [output['ll']['x'][0]],
                                                                   [output['ll']['y'][0]])

            output['lr']['x'][1], output['lr']['y'][1] = transform(src['crs'], self.projection,
                                                                   [output['lr']['x'][0]],
                                                                   [output['lr']['y'][0]])

            dst_corner_ys = [output[k]['y'][1][0] for k in output.keys()]
            dst_corner_xs = [output[k]['x'][1][0] for k in output.keys()]
            y_pixel = abs(max(dst_corner_ys) - min(dst_corner_ys)) / shape[0]
            x_pixel = abs(max(dst_corner_xs) - min(dst_corner_xs)) / shape[1]

            return (min(dst_corner_xs), x_pixel, 0.0, max(dst_corner_ys), 0.0, -y_pixel)


    def _get_image_data(self):
        src = rasterio.open(self.bands_path[-1])

        # Get pixel size from source
        self.pixel = src.affine[0]

        # Only collect src data that is needed and delete the rest
        image_data = {
            'transform': src.transform,
            'crs': src.crs,
            'affine': src.affine,
            'shape': src.shape,
            'dst_transform': None
        }

        image_data['dst_transform'] = self._get_boundaries(image_data, image_data['shape'])

        return image_data


    def _read_bands(self):
        """ Reads a band with rasterio """
        bands = []
        for i, band in enumerate(self.bands_path):
            bands.append(rasterio.open(band).read(1))
        return bands

    def _warp(self, proj_data, bands, new_bands):
        for i, band in enumerate(bands):
            print "Projecting band " +  self.bands[i]
            reproject(band, new_bands[i], src_transform=proj_data['transform'], src_crs=proj_data['crs'],
                      dst_transform=proj_data['dst_transform'], dst_crs=self.dst_crs, resampling=RESAMPLING.nearest,
                      num_threads=2)


    def _generate_new_bands(self, shape):
        new_bands = []
        for i in range(0, 3):
            new_bands.append(numpy.empty(shape, dtype=numpy.uint16))

        return new_bands


    def _write_to_file(self, new_bands, **kwargs):

        # Read coverage from metafile
        coverage = self._calculate_cloud_ice_perc()



        output = rasterio.open(self.output_file, 'w', **kwargs)

        for i, band in enumerate(new_bands):
            # Color Correction
            band = self._color_correction(band, self.bands[i], 0, coverage)

            output.write_band(i + 1, img_as_ubyte(band))

            new_bands[i] = None
        print "Writing to file " + self.scene + self.bands_values + ".TIF"
        print "This file is saved to " + self.output_file
        return self.output_file

    def _color_correction(self, band, band_id, low, coverage):
        if self.bands == [4, 5]:
            return band
        else:
            print "Color correcting band " + band_id
            p_low, cloud_cut_low = self._percent_cut(band, low, 100 - (coverage * 3 / 4))
            temp = numpy.zeros(numpy.shape(band), dtype=numpy.uint16)
            cloud_divide = 65000 - coverage * 100
            mask = numpy.logical_and(band < cloud_cut_low, band > 0)
            temp[mask] = rescale_intensity(band[mask], in_range=(p_low, cloud_cut_low), out_range=(256, cloud_divide))
            temp[band >= cloud_cut_low] = rescale_intensity(band[band >= cloud_cut_low],
                                                            out_range=(cloud_divide, 65535))
            return temp

    def _percent_cut(self, color, low, high):
        return numpy.percentile(color[numpy.logical_and(color > 0, color < 65535)], (low, high))

    def _calculate_cloud_ice_perc(self):
        """ Return the percentage of pixels that are either cloud or snow according to metafile.
        """
        if self.satellite == "landsat":
            f = open( self.scene_path + self.scene + '_MTL.txt', 'r')
            f = f.read()
            for item in f.split("\n"):
                if "CLOUD_COVER =" in item:
                    perc = item.strip().replace("CLOUD_COVER =", "")
                    perc = float(perc)

        elif self.satellite == "sentinel":
            with open(self.scene_path + 'tileInfo.json') as data_file:
                data = json.load(data_file)
                perc = data["cloudyPixelPercentage"]
                if perc == 0:
                    perc = 0.1
        print "The cloud coverage is " + str(perc) + "%"
        return perc

    def run(self):
        """ Executes the image processing.
        :returns:
            (String) the path to the processed image
        """

        print 'Image processing started for scene ' + self.scene + " and bands " + self.bands_values

        bands = self._read_bands()
        image_data = self._get_image_data()
        new_bands = self._generate_new_bands(image_data['shape'])
        self._warp(image_data, bands, new_bands)

        # Bands are no longer needed
        del bands

        rasterio_options = {
            'driver': 'GTiff',
            'width': image_data['shape'][1],
            'height': image_data['shape'][0],
            'count': 3,
            'dtype': numpy.uint8,
            'nodata': 0,
            'transform': image_data['dst_transform'],
            'photometric': 'RGB',
            'crs': self.dst_crs
        }

        return self._write_to_file(new_bands, **rasterio_options)


class PanSharpen(Processing):

    def __init__(self, scene, bands, satellite):
        super(PanSharpen, self).__init__(scene, bands, satellite)
        self.band8 = self.bands[3]

    def run(self):
        """ Executes the pansharpen image processing.
        :returns:
            (String) the path to the processed image
        """

        print 'PanSharpened Image processing started for bands'


        bands = self._read_bands()

        image_data = self._get_image_data()

        new_bands = self._generate_new_bands(image_data['shape'])

        bands[:3] = self._rescale(bands[:3])
        new_bands.append(numpy.empty(image_data['shape'], dtype=numpy.uint16))

        self._warp(image_data, bands, new_bands)

        # Bands are no longer needed
        del bands

        # Calculate pan band
        pan = self._pansize(new_bands)
        del self.bands[3]
        del new_bands[3]

        rasterio_options = {
            'driver': 'GTiff',
            'width': image_data['shape'][1],
            'height': image_data['shape'][0],
            'count': 3,
            'dtype': numpy.uint8,
            'nodata': 0,
            'transform': image_data['dst_transform'],
            'photometric': 'RGB',
            'crs': self.dst_crs
        }

        return self._write_to_file(new_bands, pan, **rasterio_options)


    def _write_to_file(self, new_bands, pan, **kwargs):

        # Read coverage from QBA
        coverage = self._calculate_cloud_ice_perc()

        print"Final Steps"

        output = rasterio.open(self.output_file, 'w', **kwargs)

        for i, band in enumerate(new_bands):
            print "started final step for " + str(i)
            # Color Correction
            band = numpy.multiply(band, pan)
            band = self._color_correction(band, self.bands[i], 0, coverage)

            output.write_band(i + 1, img_as_ubyte(band))

            new_bands[i] = None

        print "Writing to file"

        return self.output_file

    def _pansize(self, bands):

        print 'Calculating Pan Ratio'

        m = numpy.add(bands[0], bands[1])
        m = numpy.add(m, bands[2])
        pan = numpy.multiply(numpy.nan_to_num(numpy.true_divide(1, m)), bands[3])
        return pan

    def _rescale(self, bands):
        """ Rescale bands """
        # self.output("Rescaling", normal=True, arrow=True)

        for key, band in enumerate(bands):
            print "processing"
            # self.output("band %s" % self.bands[key], normal=True, color='green', indent=1)
            bands[key] = sktransform.rescale(band, 2)
            bands[key] = (bands[key] * 65535).astype('uint16')

        return bands
