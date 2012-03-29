#!/usr/bin/python
# -*- coding: utf-8 -*-

# ZVIS (c) 2012 Adam Radziszewski.
# This is free software. See LICENCE for details.

from PIL import Image, ImageDraw
#from PythonMagick import Image

import sys, os
from optparse import OptionParser
import ConfigParser

import snd

descr = """%prog [options] CONFIGFILE OUTDIR

Generates visualisation for the audiotracks specified in CONFIGFILE.
"""

def load_image(path):
	return Image.open(path).convert('RGBA')

class Layer(object):
	def __init__(self, conf_dir, fps, size, props):
		self.conf_dir = conf_dir
		self.fps = fps
		self.size = size
		self.props = props
		self.data = None # some data object for every frame
		self.load()

class ImageLayer(Layer):
	"""Static image whose opacity is controlled by audio volume."""
	def load(self):
		"""Reads audio file and stores volume points corresponding
		to each frame."""
		# load the layer 
		self.image = load_image(
			os.path.join(self.conf_dir, self.props['image']))
		# prepare all-transparent channel for help
		self.alpha = Image.new('RGBA', self.size, (0, 0, 0, 0)).getdata(3)
		# load data as floats corresponding to volume values in audio
		self.data = snd.get_volume_points(
			os.path.join(self.conf_dir, self.props['audio']), self.fps)
	
	def draw(self, canvas, num_frame):
		if num_frame < len(self.data):
			vpoint = self.data[num_frame]
			
			# dirty way of gatting overlays with proper alpha channel
			if vpoint <= 0.0:
				newalpha = self.alpha.copy()
			else:
				forealpha = self.image.getdata(3)
				inv = 1.0 / vpoint
				newalpha = self.alpha.chop_add(forealpha, inv, 0.0)
			newfore = self.image.copy()
			newfore.im.putband(newalpha, 3)
			canvas.paste(self.image, None, newfore)

class SpectroLayer(Layer):
	"""Animated spectrogram created from audio FFT."""
	def load(self):
		# horizontal scaling factor: 2 => shifting 2 pixels per frame
		self.rate = int(self.props.get('rate', 1))
		# vertical scaling factor: 4 => each fft point will take up 4 pixels
		yscale = int(self.props.get('yscale', 1))
		fft_y = self.size[1] / yscale
		# load data
		self.data = snd.get_fft_points(
			os.path.join(self.conf_dir, self.props['audio']),
			self.fps, fft_y, self.rate)
		
		# colour as list
		self.colour = map(int, self.props['colour'].split(','))
		# prepare image containing whole spectrogram
		x_pad = self.size[0] / 2
		self.specimg = Image.new('RGBA', (len(self.data) + x_pad, self.size[1]))
		draw = ImageDraw.Draw(self.specimg)
		for pos, spectrum in enumerate(self.data):
			for y in xrange(self.size[1]):
				val = spectrum[y / yscale]
				draw.point(
					(pos + x_pad, self.size[1] - y - 1),
					tuple(self.colour + [255*(val * val)/160]))
	
	def draw(self, canvas, num_frame):
		layer = self.specimg.crop(
			(self.rate * num_frame, 0,
				self.rate * num_frame + self.size[0], self.size[1]))
		canvas.paste(layer, None, layer)


layers_by_props = {
	'image': ImageLayer,
	'colour': SpectroLayer
	}

class Visualisation(object):
	def __init__(self, config_path):
		self.conf_dir, conf_fname = os.path.split(config_path)
		with open(config_path) as config_file:
			self.conf = ConfigParser.RawConfigParser()
			self.conf.readfp(config_file)
		
		self.bg = load_image(
			os.path.join(self.conf_dir, self.conf.get('general', 'bg')))
		self.fps = self.conf.getint('general', 'fps')
	
	def _mk_layer(self, props):
		layer = None
		for prop in props:
			if prop in layers_by_props:
				layer = layers_by_props[prop]
				break
		if layer is None:
			raise KeyError(
				'unknown layer for %s' % props['audio'])
		l = layer(self.conf_dir, self.fps, self.bg.size, props)
		print 'Layer for %s prepared' % props['audio']
		return l
	
	def render(self, out_dir):
		# load layer defs
		layer_names = sorted(sec for sec in self.conf.sections()
			if sec != 'general')
		layers = [self._mk_layer(self.conf._sections[name])
			for name in layer_names]
		# load all images assiated to layers
		
		for num_frame in xrange(len(layers[0].data)):
			my_img = self.bg.copy()
			for layer_num, layer_name in enumerate(layer_names):
				layer = layers[layer_num]
				layer.draw(my_img, num_frame)
			my_img.save(
				os.path.join(out_dir, 'frame%06d.jpg' % num_frame),
				quality=100)
			print num_frame

if __name__ == '__main__':
	parser = OptionParser(usage=descr)
	#parser.add_option('-f', '--fps', type='int', action='store',
		#dest='fps', default='25',
		#help='set frames per second; default: 25')
	
	(options, args) = parser.parse_args()
	
	if len(args) < 2:
		sys.stderr.write('You need to provide a config file and output dir.\n')
		sys.stderr.write('See --help\n')
		sys.exit(1)
	else:
		config_path, out_dir = args
		vis = Visualisation(config_path)
		vis.render(out_dir)

