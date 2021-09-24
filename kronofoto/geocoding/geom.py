from collections import namedtuple

class Location(namedtuple('Location_', ['centroid', 'bounds'])):
    def __eq__(self, other):
        return self.centroid.equals(other.centroid) and self.bounds.equals(other.bounds)


class Bounds(namedtuple('Bounds_', ['xmin', 'ymin', 'xmax', 'ymax'])):
    def shift_to_enclose(self, point):
        x = point[0]
        bounds = self
        while bounds.xmin > x:
            bounds = bounds._replace(xmin=bounds.xmin - 360)
        while bounds.xmax < x:
            bounds = bounds._replace(xmax=bounds.xmax + 360)
        return bounds

    def astuple(self):
        return (self.xmin, self.ymin, self.xmax, self.ymax)

    def as_shifted_bounds(self, boundary=180):
        if self.xmax >= self.xmin:
            return [self]
        else:
            return [
                Bounds(xmin=self.xmin, ymin=self.ymin, xmax=boundary, ymax=self.ymax),
                Bounds(xmin=-boundary, ymin=self.ymin, xmax=self.xmax, ymax=self.ymax),
            ]



