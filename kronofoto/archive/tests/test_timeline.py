from django.test import SimpleTestCase, tag


@tag("fast")
class TimelineDisplay(SimpleTestCase):
    def assertIsPosition(self, obj):
        for key in ('x', 'y', 'width', 'height'):
            self.assertIn(key, obj)
            self.assertTrue(isinstance(obj[key], int) or isinstance(obj[key], float))

    # Timeline svg is a normal view now.
    # Test (temporarily?) disabled.
    def estShouldDefineMinorMarkerPositions(self):
        years = [(year, '/{}'.format(year), '/{}.json'.format(year)) for year in [1900, 1901, 1902, 1903, 1904, 1905]]
        result = timeline.make_timeline(years, 1900, 1905, width=60)
        self.assertIn('majornotches', result)
        self.assertEqual(len(result['majornotches']), 1)
        for notch in result['majornotches']:
            for key in ('target', 'json_target', 'box', 'notch', 'label'):
                self.assertIn(key, notch)
            for key in ('box', 'notch'):
                self.assertIsPosition(notch[key])
            for key in ('text', 'x', 'y'):
                self.assertIn(key, notch['label'])
        self.assertIn('minornotches', result)
        self.assertEqual(len(result['minornotches']), 5)
        for notch in result['minornotches']:
            for key in ('target', 'json_target', 'box', 'notch'):
                self.assertIn(key, notch)
            for key in ('box', 'notch'):
                self.assertIsPosition(notch[key])
