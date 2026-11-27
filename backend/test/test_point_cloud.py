import struct
import unittest
from base64 import b64decode
from io import BytesIO
from unittest.mock import patch

import laspy
import lzf
import numpy as np

from app import create_app
from app.config.settings import DEFAULT_MYSQL_SETTINGS


class PointCloudPreviewTest(unittest.TestCase):
    def setUp(self):
        settings = {**DEFAULT_MYSQL_SETTINGS, "LOG_LEVEL": "WARNING"}
        with patch("app.load_settings", return_value=settings):
            self.client = create_app().test_client()

    def upload(self, name, content):
        return self.client.post("/api/point-clouds/preview", data={"file": (BytesIO(content), name)})

    def preview(self, name, content):
        response = self.upload(name, content)
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        data = response.get_json()["data"]
        points = np.frombuffer(b64decode(data["positions"]), dtype="<f4").reshape(-1, 3)
        points = points.astype(float) * data["scale"] + data["origin"]
        colors = data["colors"]
        rgb = np.frombuffer(b64decode(colors), dtype=np.uint8).reshape(-1, 3) if colors is not None else None
        self.assertEqual(len(points), data["previewCount"])
        return data, points, rgb

    def test_ply_vertex_fields(self):
        layout = (b"element vertex 2\nproperty uchar red\nproperty double x\n"
                  b"property double y\nproperty double z\nproperty uchar green\nproperty uchar blue\n"
                  b"element face 1\nproperty list uchar int vertex_indices\nend_header\n")
        for encoding, body in (
            ("ascii", b"255 6700000.1 0 1 0 0\n0 6700000.2 0 9 255 0\n2 0 1\n"),
            ("binary_little_endian", struct.pack("<BdddBBBdddBB", 255, 6700000.1, 0, 1, 0, 0, 0, 6700000.2, 0, 9, 255, 0)),
            ("binary_big_endian", struct.pack(">BdddBBBdddBB", 255, 6700000.1, 0, 1, 0, 0, 0, 6700000.2, 0, 9, 255, 0)),
        ):
            with self.subTest(encoding=encoding):
                data, points, rgb = self.preview("scan.PLY", f"ply\nformat {encoding} 1.0\n".encode() + layout + body)
                np.testing.assert_allclose(points, [[6700000.1, 0, 1], [6700000.2, 0, 9]], rtol=0, atol=1e-7)
                np.testing.assert_array_equal(rgb, [[255, 0, 0], [0, 255, 0]])
                self.assertEqual(data["bounds"]["max"][2], 9)

    def test_pcd_packed_rgb_and_compression(self):
        rows = [(1.0, 3.0, 5.0, 0xFF0000), (1.0, 3.0, 5.0, 0x00FF00)] * 32
        header = (b"VERSION 0.7\nFIELDS x y z rgb\nSIZE 4 4 4 4\nTYPE F F F U\n"
                  b"WIDTH 64\nHEIGHT 1\nPOINTS 64\nDATA ")
        binary = b"".join(struct.pack("<fffI", *row) for row in rows)
        column_major = b"".join(struct.pack("<64" + kind, *values)
                                for kind, values in zip("fffI", zip(*rows)))
        compressed = lzf.compress(column_major)
        compressed = struct.pack("<II", len(compressed), len(column_major)) + compressed
        for encoding, body in (
            (b"ascii", b"\n".join(b"%s %s %s %s" % tuple(str(value).encode() for value in row) for row in rows)),
            (b"binary", binary),
            (b"binary_compressed", compressed),
        ):
            with self.subTest(encoding=encoding):
                _, points, rgb = self.preview("scan.pcd", header + encoding + b"\n" + body)
                np.testing.assert_array_equal(points[0], [1, 3, 5])
                np.testing.assert_array_equal(rgb[:2], [[255, 0, 0], [0, 255, 0]])

    def test_las_and_laz_scaled_coordinates_and_rgb(self):
        header = laspy.LasHeader(point_format=3, version="1.2")
        header.offsets = np.array([500_000, 2_000_000, 0])
        cloud = laspy.LasData(header)
        cloud.x, cloud.y, cloud.z = [500_001.1, 500_002.5], [2_000_001, 2_000_002], [1, 4]
        cloud.red, cloud.green, cloud.blue = [65535, 0], [0, 65535], [0, 0]
        for extension in ("las", "laz"):
            with self.subTest(extension=extension):
                stream = BytesIO()
                cloud.write(stream, do_compress=extension == "laz")
                _, points, rgb = self.preview(f"scan.{extension}", stream.getvalue())
                np.testing.assert_allclose(points, [[500001.1, 2000001, 1], [500002.5, 2000002, 4]], rtol=0, atol=1e-7)
                np.testing.assert_array_equal(rgb, [[255, 0, 0], [0, 255, 0]])

    def test_text_headers_and_sampling_keep_rgb_aligned(self):
        body = b"\xef\xbb\xbfZ,R,X,Y,G,B\n4,50,1,2,0,0\n6,80,2,2,0,0\n7,100,3,2,0,0\nnan,255,5,2,0,0\n"
        with patch("app.service.point_cloud.MAX_PREVIEW_POINTS", 2):
            data, points, rgb = self.preview("scan.csv", body)
        self.assertEqual((data["inputCount"], data["pointCount"], data["previewCount"]), (4, 3, 2))
        self.assertEqual(data["bounds"]["max"], [3, 2, 7])
        for point, color in zip(points, rgb):
            self.assertEqual(color[0], {1: 50, 2: 80, 3: 100}[round(point[0])])

        _, points, rgb = self.preview("scan.pts", b"2\n1 2 3 15 255 0 0\n4 5 6 20 0 255 0\n")
        np.testing.assert_array_equal(points, [[1, 2, 3], [4, 5, 6]])
        np.testing.assert_array_equal(rgb, [[255, 0, 0], [0, 255, 0]])

    def test_rejects_missing_unsupported_malformed_and_oversized_inputs(self):
        self.assertEqual(self.client.post("/api/point-clouds/preview").status_code, 400)
        self.assertEqual(self.upload("scan.bin", b"1 2 3").status_code, 415)
        self.assertEqual(self.upload("scan.pts", b"3\n1 2 3\n").status_code, 400)
        self.assertEqual(self.upload("scan.ply", b"ply\nformat binary_little_endian 1.0\n").status_code, 400)
        self.assertEqual(self.upload("scan.laz", b"not a LAS file").status_code, 400)
        with patch("app.service.point_cloud.MAX_FILE_BYTES", 4):
            self.assertEqual(self.upload("scan.xyz", b"1 2 3").status_code, 413)
