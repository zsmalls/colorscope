#!/usr/bin/python
import cv2
import numpy as np
from scipy import ndimage
from skimage import morphology
import math
import json

#main class
#==========
class Filter:
    '''Mophological processing image class'''

    def __init__(self):
        self.epsilon = 15

    def get_json(self, filename):
        '''Returns: json string file with the format:
        z1: [x1, y1, x2, y2, x3, y3, ..., width]
        z2: [x1, y1, x2, y2, ..., width]'''

        orig_img = cv2.imread(filename)
        img = self.skeletonize(orig_img)
        skeleton = img.astype('uint8') * 255
        
        img = self.hit_or_miss_junctions(img)
        img = img.astype('uint8') * 255
        
        kernel = np.ones((3, 3))
        img = cv2.morphologyEx(img, cv2.MORPH_DILATE, kernel)
        difference = skeleton - img
        img_segments = cv2.threshold(difference, 0, 255, cv2.THRESH_OTSU)[1]
        img = self.hit_or_miss_linends(img_segments > 0)

        line_ends = self.get_line_ends(img)
        segments  = self.build_segments(img_segments, line_ends)
        intervals = self.build_intervals(segments)

        gray_img   = cv2.cvtColor(orig_img, cv2.COLOR_BGR2GRAY)
        thresh_img = cv2.threshold(gray_img, 0, 255, cv2.THRESH_OTSU)[1]
        self.find_widths(intervals, thresh_img > 0)

        segments_dict = self.get_segments(intervals)
        return json.dumps(segments_dict)        


    def skeletonize(self, img):
        '''It builds a morphological skeleton from
        a mask of the streets'''

        gray_img   = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thresh_img = cv2.threshold(gray_img, 0, 255, cv2.THRESH_OTSU)[1]
        thresh_img = ~thresh_img
        return morphology.skeletonize(thresh_img > 0)


    def hit_or_miss_junctions(self, bin_img):
        '''Find the junctions in the skeleton.
        Returns a binary image with all the junctions found'''

        img      = np.zeros_like(bin_img, dtype="bool")
        struct   = [np.array([[1, 0, 1], [0, 1, 0], [0, 1, 0]]),
                    np.array([[0, 1, 0], [0, 1, 1], [1, 0, 0]]),
                    np.array([[0, 0, 1], [1, 1, 0], [0, 0, 1]]),
                    np.array([[1, 0, 0], [0, 1, 1], [0, 1, 0]]),
                    np.array([[0, 1, 0], [0, 1, 0], [1, 0, 1]]),  
                    np.array([[0, 0, 1], [1, 1, 0], [0, 1, 0]]),
                    np.array([[1, 0, 0], [0, 1, 1], [1, 0, 0]]),
                    np.array([[0, 1, 0], [1, 1, 0], [0, 0, 1]]),
                    np.array([[1, 0, 0], [0, 1, 0], [1, 0, 1]]),
                    np.array([[1, 0, 1], [0, 1, 0], [1, 0, 1]]),
                    np.array([[1, 0, 1], [0, 1, 0], [0, 0, 1]]),
                    np.array([[0, 0, 1], [0, 1, 0], [1, 0, 1]]),
                    np.array([[0, 1, 0], [1, 1, 1], [0, 0, 0]]),
                    np.array([[0, 1, 0], [0, 1, 1], [0, 1, 0]]),
                    np.array([[0, 1, 0], [1, 1, 0], [0, 1, 0]]),
                    np.array([[0, 0, 0], [1, 1, 1], [0, 1, 0]])]
        for s in struct:
            img |= ndimage.morphology.binary_hit_or_miss(bin_img, structure1=s)
        return img


    def hit_or_miss_linends(self, bin_img):
        '''Find the line ends in the image.
        Returns a binary image with all the line ends found'''

        img = np.zeros_like(bin_img, dtype="bool")
        struct = [np.array([[0, 0, 0], [1, 1, 0], [0, 0, 0]]),
                  np.array([[0, 0, 0], [0, 1, 0], [0, 1, 0]]),
                  np.array([[0, 0, 0], [0, 1, 1], [0, 0, 0]]),
                  np.array([[0, 1, 0], [0, 1, 0], [0, 0, 0]]),
                  np.array([[0, 0, 0], [0, 1, 0], [1, 0, 0]]),
                  np.array([[0, 0, 0], [0, 1, 0], [0, 0, 1]]),
                  np.array([[0, 0, 1], [0, 1, 0], [0, 0, 0]]),
                  np.array([[1, 0, 0], [0, 1, 0], [0, 0, 0]])]
        for s in struct:
            img |= ndimage.morphology.binary_hit_or_miss(bin_img, structure1=s)
        return img


    def get_line_ends(self, bin_img):
        '''Get the coordinates of all the line ends found'''

        line_ends = []
        for i in range(bin_img.shape[0]):
            for j in range(bin_img.shape[1]):
                if bin_img[i][j] > 0:
                    line_ends.append([i, j])
        return line_ends


    def build_segments(self, bin_img, line_ends):
        '''Using a binary image of the streets, it builds a
        an array of segments starting from line ends'''

        segments = []
        visited = 2
        for end in line_ends:
            i = end[0]
            if i != visited:
                segment = self.build_segment(end, bin_img)
                segments.append(segment)
        return segments


    def build_segment(self, line_end, bin_img):
        '''Auxiliary method for build_segments().
        It visits the 8-neighborhood in order to find
        connected components that makes up a segment'''

        segment = Segment(bin_img)
        row = line_end[0]
        col = line_end[1]
        segment.add(row, col)
        h, w = bin_img.shape
        visited = 2
        bin_img[row][col] = visited
        while True:
            neighbor_row = -1
            neighbor_col = -1
            for i in range(-1, 2):
                x = i + col
                if x < 0 or x >= w: 
                    continue
                for j in range(-1, 2):
                    y = j + row
                    if y < 0 or y >= h:
                        continue
                    p = bin_img[y][x]
                    if (p > visited):
                        segment.add(y, x)
                        bin_img[y][x] = visited
                        neighbor_row = y
                        neighbor_col = x
            row = neighbor_row
            col = neighbor_col
            if row == -1:
                break
        return segment


    def build_intervals(self, segments):
        '''Discretize a segment in intervals (minor optimization)'''

        intervals = []
        for segment in segments:
            interval = []
            d = int(math.ceil(segment.length / self.epsilon))
            for i in range(0, d+1):
                if i < d:
                    interval.append(segment.points[i*self.epsilon])
                else:
                    length = segment.length
                    interval.append(segment.points[length-1])
            intervals.append(interval)
        return intervals

    def find_widths(self, intervals, gradient_img):
        '''Find the widths of the streets using the idea
        of a "growing circle" running through the roads'''

        rows = gradient_img.shape[0]
        cols = gradient_img.shape[1]
        for interval in intervals:
            for p in interval:
                radius = 1
                while True:
                    circle = self.draw_circle(p, rows, cols, radius)
                    temp_img = gradient_img & circle
                    if temp_img.max() > 0:
                        p.width = radius
                        break
                    radius += 2


    def draw_circle(self, point, rows, cols, radius):
        '''Returns a drawn circle in a frame'''

        cy = point.row
        cx = point.col
        y, x = np.ogrid[-cy:rows-cy, -cx:cols-cx]
        mask = x*x + y*y <= radius * radius
        array = np.zeros((rows, cols))
        array[mask] = 255
        return array > 0

    def get_segments(self, intervals):
        '''Construct a list of segments with the
        average width at the end. This method is used
        for web API purposes'''

        segments = {}
        i = 1
        for s in intervals:
            segment = []
            avg = 0
            for p in s:
                segment.append(p.col)
                segment.append(p.row)
                avg += p.width
            avg /= float(len(s))
            segment.append(avg)
            segments['z' + str(i)] = segment
            i += 1
        return segments


#--------------------------------------------------------------
class Segment:
    def __init__(self, img):
        self.points = []
        self.img = img
        self.length = 0

    def add(self, row, col):
        point = Point(row, col)
        self.points.append(point)
        self.length += 1


#--------------------------------------------------------------
class Point:
    def __init__(self, row, col):
        self.row = row
        self.col = col
        self.width = 1


#main program
#============
if __name__ == '__main__':
    app = Filter()
