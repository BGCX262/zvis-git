# -*- coding: utf-8 -*-
from scikits.audiolab import Sndfile
from numpy.fft import fft
import math

# ZVIS (c) 2012 Adam Radziszewski.
# This is free software. See LICENCE for details.

VOL_BUFFSIZE = 1024 # buff size for reading frames

def get_volume_points(sound_filename, fps, inertia = 0.03):
	"""Reads an audio file and generates a list of float values corresponding
	to the volume assosciated with each keyframe."""
	f = Sndfile(sound_filename, 'r')
	k = 1.0 - 1.0 / (inertia * f.samplerate)
	vol = 0.0
	framepos = 0L
	divisor = f.samplerate / fps # should be integer
	points = []
	while framepos < f.nframes:
		read_len = (
			VOL_BUFFSIZE if (framepos + VOL_BUFFSIZE < f.nframes)
			else f.nframes - framepos)
		frames = f.read_frames(read_len)
		for frame in frames:
			vol *= k
			# is frame iterable or just one chan?
			if getattr(frame, '__iter__', False):
				loudest = max(abs(chan) for chan in frame)
			else:
				loudest = abs(frame)
			if loudest > vol:
				vol = loudest
			if framepos % divisor == 0:
				points.append(vol)
			framepos += 1
	f.close()
	# maximise
	min_val = min(points)
	max_val = max(points)
	if min_val < max_val:
		points = [(val - min_val) / (max_val - min_val) for val in points]
	else:
		points = [0.0 for _ in points]
	# get log values (dB)
	#C1 = 0.0
	#C2 = 20.0 / math.log(10.0)
	#small = 0.4
	#points = [C1 + C2 * math.log(val + small) for val in points]
	return points


def get_fft_points(sound_filename, fps, fft_pixels, rate = 1, fourierwidth = 0.3):
	"""TODO
	will generate rate points per frame
	Based on the script from
	http://classicalconvert.com/2008/04/
	how-to-visualize-music-using-animated-spectrograms-with
	-open-source-everything/"""
	f = Sndfile(sound_filename, 'r')
	divisor = f.samplerate / (rate * fps) # should be integer
	points = []
	framepos = 0L
	while framepos < f.nframes:
		read_len = (
			divisor if (framepos + divisor < f.nframes)
			else f.nframes - framepos)
		frames = f.read_frames(read_len)
		buff = []
		for frame in frames:
			# is frame iterable or just one chan?
			if getattr(frame, '__iter__', False):
				fval = sum(frame) / len(frame)
			else:
				fval = frame
			buff.append(fval)
		# TODO: trim to 1024 or so?
		outfft = fft(buff)
		spectrum = [
			(outfft[y].real
				if y < len(outfft) else 0.0)
			for y in xrange(fft_pixels)]
		points.append(spectrum)
		framepos += len(frames)
	f.close()
	# maximise
	return points
