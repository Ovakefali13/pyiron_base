# coding: utf-8
# Copyright (c) Max-Planck-Institut für Eisenforschung GmbH - Computational Materials Design (CM) Department
# Distributed under the terms of "New BSD License", see the LICENSE file.

import os
import sys
from io import StringIO
import numpy as np
from pyiron_base.generic.hdfio import FileHDFio, _is_ragged_in_1st_dim_only
from pyiron_base._tests import PyironTestCase
import unittest


class TestFileHDFio(PyironTestCase):
    @classmethod
    def setUpClass(cls):
        cls.current_dir = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
        cls.empty_hdf5 = FileHDFio(file_name=cls.current_dir + "/filehdfio_empty.h5")
        cls.full_hdf5 = FileHDFio(file_name=cls.current_dir + "/filehdfio_full.h5")
        cls.i_o_hdf5 = FileHDFio(file_name=cls.current_dir + "/filehdfio_io.h5")
        cls.es_hdf5 = FileHDFio(
            file_name=cls.current_dir + "/../static/dft/es_hdf.h5"
        )
        with cls.full_hdf5.open("content") as hdf:
            hdf["array"] = np.array([1, 2, 3, 4, 5, 6])
            hdf["array_3d"] = np.array([[1, 2, 3], [4, 5, 6]])
            hdf["traj"] = np.array([[[1, 2, 3], [4, 5, 6]], [[7, 8, 9]]], dtype=object)
            hdf["dict"] = {"key_1": 1, "key_2": "hallo"}
            hdf["dict_numpy"] = {"key_1": 1, "key_2": np.array([1, 2, 3, 4, 5, 6])}
            hdf['indices'] = np.array([1, 1, 1, 1, 6], dtype=int)
            with hdf.open('group') as grp:
                grp['some_entry'] = 'present'
        with cls.i_o_hdf5.open("content") as hdf:
            hdf["exists"] = True
        # Open and store value in a hdf file to use test_remove_file on it, do not use otherwise
        cls.to_be_removed_hdf = FileHDFio(file_name=cls.current_dir + '/filehdfio_tbr.h5')
        with cls.to_be_removed_hdf.open('content') as hdf:
            hdf['value'] = 1
        # Remains open to be closed by test_close, do not use otherwise
        cls.opened_hdf = cls.full_hdf5.open("content")

    @classmethod
    def tearDownClass(cls):
        cls.current_dir = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
        os.remove(cls.current_dir + "/filehdfio_full.h5")
        os.remove(cls.current_dir + "/filehdfio_io.h5")

    def _check_full_hdf_values(self, hdf):
        with self.subTest('content/array'):
            array = hdf["content/array"]
            self.assertTrue(
                np.array_equal(array, np.array([1, 2, 3, 4, 5, 6]))
            )
            self.assertIsInstance(array, np.ndarray)
            self.assertEqual(array.dtype, np.dtype(int))

        with self.subTest('content/array_3d'):
            array = hdf["content"]["array_3d"]
            self.assertTrue(
                np.array_equal(
                    array,
                    np.array([[1, 2, 3], [4, 5, 6]]),
                )
            )
            self.assertIsInstance(array, np.ndarray)
            self.assertEqual(array.dtype, np.dtype(int))

        with self.subTest('content/indices'):
            array = hdf['content/indices']
            self.assertTrue(
                np.array_equal(
                    array,
                    np.array([1, 1, 1, 1, 6])
                )
            )
            self.assertIsInstance(array, np.ndarray)
            self.assertEqual(array.dtype, np.dtype(int))

        with self.subTest('content/traj'):
            array = hdf["content/traj"]
            self.assertTrue(
                np.array_equal(
                    array[0], np.array([[1, 2, 3], [4, 5, 6]])
                )
            )
            self.assertTrue(
                np.array_equal(
                    array[1], np.array([[7, 8, 9]])
                )
            )
            self.assertIsInstance(array, np.ndarray)
            self.assertEqual(array.dtype, np.dtype(object))

        with self.subTest('content/dict'):
            content_dict = hdf["content/dict"]
            self.assertEqual(content_dict["key_1"], 1)
            self.assertEqual(content_dict["key_2"], "hallo")
            self.assertIsInstance(content_dict, dict)

        with self.subTest('content/dict_numpy'):
            content_dict = hdf["content/dict_numpy"]
            self.assertEqual(content_dict["key_1"], 1)
            self.assertTrue(
                np.array_equal(
                    content_dict["key_2"],
                    np.array([1, 2, 3, 4, 5, 6]),
                )
            )

        with self.subTest('content/group/some_entry'):
            self.assertEqual(hdf['content/group/some_entry'], 'present')

    def test__is_convertable_dtype_object_array(self):
        object_array_with_lists = np.array([[[1, 2, 3], [2, 3, 4]], [[4, 5, 6]]], dtype=object)
        int_array_as_objects_array = np.array([[1, 2, 3], [3, 4, 5]], dtype=object)
        float_array_as_objects_array = np.array([[1.1, 1.3, 1.5], [2, 2.1, 2.2]], dtype=object)
        object_array_with_none = np.array([[1.1, None, 1.5], [None, 2.1, 2.2]], dtype=object)

        self.assertFalse(self.i_o_hdf5._is_convertable_dtype_object_array(object_array_with_lists))
        self.assertTrue(self.i_o_hdf5._is_convertable_dtype_object_array(int_array_as_objects_array))
        self.assertTrue(self.i_o_hdf5._is_convertable_dtype_object_array(float_array_as_objects_array))
        self.assertTrue(self.i_o_hdf5._is_convertable_dtype_object_array(object_array_with_none),
                        msg="This array should be considered convertable, since first and last element are numbers.")

    def test__convert_dtype_obj_array(self):
        object_array_with_lists = np.array([[[1, 2, 3], [2, 3, 4]], [[4, 5, 6]]], dtype=object)
        int_array_as_objects_array = np.array([[1, 2, 3], [3, 4, 5]], dtype=object)
        float_array_as_objects_array = np.array([[1.1, 1.3, 1.5], [2, 2.1, 2.2]], dtype=object)
        object_array_with_none = np.array([[1.1, None, 1.5], [None, 2.1, 2.2]], dtype=object)

        self.assertIs(self.i_o_hdf5._convert_dtype_obj_array(object_array_with_lists), object_array_with_lists)
        self.assertIs(self.i_o_hdf5._convert_dtype_obj_array(object_array_with_none), object_array_with_none)

        array = self.i_o_hdf5._convert_dtype_obj_array(int_array_as_objects_array)
        self.assertTrue(np.array_equal(array, int_array_as_objects_array))
        self.assertEqual(array.dtype, np.dtype(int))

        array = self.i_o_hdf5._convert_dtype_obj_array(float_array_as_objects_array)
        self.assertTrue(np.array_equal(array, float_array_as_objects_array))
        self.assertEqual(array.dtype, np.dtype(float))

    def test_array_type_conversion(self):
        object_array_with_lists = np.array([[[1, 2, 3], [2, 3, 4]], [[4, 5, 6]]], dtype=object)
        int_array_as_objects_array = np.array([[1, 2, 3], [3, 4, 5]], dtype=object)
        float_array_as_objects_array = np.array([[1.1, 1.3, 1.5], [2, 2.1, 2.2]], dtype=object)

        hdf = self.i_o_hdf5.open("arrays")

        hdf['object_array_with_lists'] = object_array_with_lists
        hdf['int_array_as_objects_array'] = int_array_as_objects_array
        hdf['float_array_as_objects_array'] = float_array_as_objects_array

        with self.subTest("object_array_with_lists"):
            array = hdf['object_array_with_lists']
            np.array_equal(array, object_array_with_lists)
            self.assertIsInstance(array, np.ndarray)
            self.assertEqual(array.dtype, np.dtype(object), msg="dtype=object array falsely converted.")

        #  Here I got:  TypeError: Object dtype dtype('O') has no native HDF5 equivalent
        #
        # object_array_with_none = np.array([[1.1, None, 1.5], [None, 2.1, 2.2]], dtype=object)
        # hdf['object_array_with_none'] = object_array_with_none
        # with self.subTest("object_array_with_none"):
        #     array = hdf['object_array_with_none']
        #     np.array_equal(array, object_array_with_none)
        #     self.assertIsInstance(array, np.ndarray)
        #     self.assertTrue(array.dtype == np.dtype(object))

        with self.subTest('int_array_as_objects_array'):
            array = hdf['int_array_as_objects_array']
            np.array_equal(array, int_array_as_objects_array)
            self.assertIsInstance(array, np.ndarray)
            self.assertEqual(array.dtype, np.dtype(int), msg="dtype=object array containing only int not converted "
                                                             "to dtype int array.")

        with self.subTest('float_array_as_objects_array'):
            array = hdf['float_array_as_objects_array']
            np.array_equal(array, float_array_as_objects_array)
            self.assertIsInstance(array, np.ndarray)
            self.assertEqual(array.dtype, np.dtype(float), msg="dtype=object array containing only float not converted"
                                                               " to dtype float array.")

        hdf.remove_group()

    def test_get_item(self):
        self._check_full_hdf_values(self.full_hdf5)
        # Test leaving to pyiron Project at hdf file location:
        pr = self.full_hdf5['content/..']
        from pyiron_base import Project
        self.assertIsInstance(pr, Project)
        self.assertEqual(pr.path, self.full_hdf5.file_path + '/')
        # Test leaving to pyiron Project at other than hdf file location:
        pr = self.full_hdf5['..']
        self.assertIsInstance(pr, Project)
        self.assertEqual(pr.path.replace("\\", "/"),
                         os.path.normpath(
                                os.path.join(self.full_hdf5.file_path, '..')
                             ).replace("\\", "/") + '/'
                         )
        # Test getting a new FileHDFio object:
        group_hdf = self.full_hdf5['content/group']
        self.assertIsInstance(group_hdf, FileHDFio)
        self.assertEqual(group_hdf.h5_path, '/content/group')
        # Test getting the parent FileHDFio object:
        content_hdf = group_hdf['..']
        self.assertIsInstance(content_hdf, FileHDFio)
        self.assertEqual(content_hdf.h5_path, self.full_hdf5.h5_path + 'content')
        # Getting the '/' of the hdf would result in a path which already belongs to the project.
        # Therefore, the project is returned instead.
        pr = content_hdf['..']
        self.assertIsInstance(pr, Project)
        self.assertEqual(pr.path, self.full_hdf5.file_path + '/')
        # Test getting the same object directly:
        pr = group_hdf['../..']
        self.assertIsInstance(pr, Project)
        self.assertEqual(pr.path, self.full_hdf5.file_path + '/')

    def test_file_name(self):
        self.assertEqual(
            self.empty_hdf5.file_name, self.current_dir + "/filehdfio_empty.h5"
        )
        self.assertEqual(
            self.full_hdf5.file_name, self.current_dir + "/filehdfio_full.h5"
        )

    def test_h5_path(self):
        self.assertEqual(self.full_hdf5.h5_path, '/')

    def test_open(self):
        opened_hdf = self.full_hdf5.open('content')
        self.assertEqual(opened_hdf.h5_path, '/content')
        self.assertEqual(opened_hdf.history[-1], 'content')

    def test_close(self):
        self.opened_hdf.close()
        self.assertEqual(self.opened_hdf.h5_path, '/')

    def test_remove_file(self):
        path = self.to_be_removed_hdf.file_name
        self.to_be_removed_hdf.remove_file()
        self.assertFalse(os.path.isfile(path))

    def test_get_from_table(self):
        pass

    def test_get_pandas(self):
        pass

    def test_get(self):
        self.assertEqual(self.full_hdf5.get("doesnotexist", default=42), 42,
                         "default value not returned when value doesn't exist.")
        self.assertTrue(np.array_equal(
            self.full_hdf5.get("content/array", default=42),
            np.array([1, 2, 3, 4, 5, 6])
        ), "default value returned when value does exist.")
        with self.assertRaises(ValueError):
            self.empty_hdf5.get('non_existing_key')

    def test_hd_copy(self):
        new_hdf_file = os.path.join(self.current_dir, 'copy_full.h5')
        new_hdf = FileHDFio(file_name=new_hdf_file)
        new_hdf = self.full_hdf5.hd_copy(self.full_hdf5, new_hdf)
        self._check_full_hdf_values(new_hdf)
        os.remove(new_hdf_file)

    def test_groups(self):
        groups = self.full_hdf5.groups()
        # _filter is actually relies on the _filter property of the Project, thus groups does not do anything.
        self.assertIsInstance(groups, FileHDFio)

    def test_rewrite_hdf5(self):
        pass

    def test_to_object(self):
        pass

    def test_put(self):
        self.i_o_hdf5.put('answer', 42)
        self.assertEqual(self.i_o_hdf5['answer'], 42)

    def test_list_all(self):
        empty_file_dict = self.empty_hdf5.list_all()
        self.assertEqual(empty_file_dict["groups"], [])
        self.assertEqual(empty_file_dict["nodes"], [])
        es_file_dict = self.es_hdf5.list_all()
        self.assertEqual(es_file_dict["groups"], ["es_new", "es_old"])
        self.assertEqual(es_file_dict["nodes"], [])
        es_group_dict = self.es_hdf5["es_new"].list_all()
        self.assertEqual(es_group_dict["groups"], ["dos"])
        self.assertEqual(
            es_group_dict["nodes"],
            ["TYPE", "efermi", "eig_matrix", "k_points", "k_weights", "occ_matrix"],
        )

    def test_list_nodes(self):
        self.assertEqual(self.empty_hdf5.list_nodes(), [])
        self.assertEqual(
            self.es_hdf5["es_new"].list_nodes(),
            ["TYPE", "efermi", "eig_matrix", "k_points", "k_weights", "occ_matrix"],
        )

    def test_list_groups(self):
        self.assertEqual(self.empty_hdf5.list_groups(), [])
        self.assertEqual(self.es_hdf5.list_groups(), ["es_new", "es_old"])

    def test_listdirs(self):
        self.assertEqual(self.empty_hdf5.listdirs(), [])
        self.assertEqual(self.es_hdf5.listdirs(), ["es_new", "es_old"])

    def test_show_hdf(self):
        sys_stdout = sys.stdout
        result = StringIO()
        sys.stdout = result
        self.full_hdf5.show_hdf()
        result_string = result.getvalue()
        sys.stdout = sys_stdout
        self.assertEqual(result_string,
                         'group:  content\n  node array\n  node array_3d\n  node dict\n  node dict_numpy\n' +
                         '  node indices\n  node traj\n  group:  group\n    node some_entry\n'
                         )

    def test_is_empty(self):
        self.assertTrue(self.empty_hdf5.is_empty)
        self.assertFalse(self.full_hdf5.is_empty)

    def test_is_root(self):
        self.assertTrue(self.full_hdf5.is_root)
        hdf = self.full_hdf5['content']
        self.assertFalse(hdf.is_root)

    def test_base_name(self):
        self.assertEqual(self.full_hdf5.base_name, 'filehdfio_full')
        self.assertEqual(self.empty_hdf5.base_name, 'filehdfio_empty')
        self.assertEqual(self.i_o_hdf5.base_name, 'filehdfio_io')

    def test_file_size(self):
        self.assertTrue(self.es_hdf5.file_size(self.es_hdf5) > 0)

    def test_get_size(self):
        self.assertTrue(self.es_hdf5.get_size(self.es_hdf5) > 0)

    def test_copy(self):
        copy = self.es_hdf5.copy()
        self.assertIsInstance(copy, FileHDFio)
        self.assertEqual(copy.h5_path, self.es_hdf5.h5_path)

    # results in an Error
    #   File "C:\Users\Siemer\pyiron_git\pyiron_base\tests\generic\test_fileHDFio.py", line 249, in test_copy_to
    #     copy = self.full_hdf5.copy_to(destination)
    #   File "C:\Users\Siemer\pyiron_git\pyiron_base\pyiron_base\generic\hdfio.py", line 355, in copy_to
    #     _internal_copy(source=f_source, source_path=self._h5_path, target=f_target,
    #   File "C:\Users\Siemer\pyiron_git\pyiron_base\pyiron_base\generic\hdfio.py", line 332, in _internal_copy
    #     source.copy(source_path, target, name=target_path)
    #   File "C:\Users\Siemer\anaconda3\envs\pyiron_git\lib\site-packages\h5py\_hl\group.py", line 494, in copy
    #     h5o.copy(source.id, self._e(source_path), dest.id, self._e(dest_path),
    #   File "h5py\_objects.pyx", line 54, in h5py._objects.with_phil.wrapper
    #   File "h5py\_objects.pyx", line 55, in h5py._objects.with_phil.wrapper
    #   File "h5py\h5o.pyx", line 217, in h5py.h5o.copy
    #   ValueError: No destination name specified (no destination name specified)
    #def test_copy_to(self):
    #    file_name = self.current_dir + '/filehdfio_tmp'
    #    destination = FileHDFio(file_name=file_name)
    #    copy = self.full_hdf5.copy_to(destination)
    #    self._check_full_hdf_values(copy)
    #    os.remove(file_name)

    def test_remove_group(self):
        grp = 'group_to_be_removed'
        hdf = self.i_o_hdf5.create_group(grp)
        # If nothing is written to the group, the creation is not reflected by the HDF5 file
        hdf['key'] = 1
        self.assertTrue(grp in self.i_o_hdf5.list_groups())
        hdf.remove_group()
        self.assertFalse(grp in self.i_o_hdf5.list_nodes())
        # This should not raise an error, albeit the group of hdf is removed
        hdf.remove_group()

    def test_ragged_array(self):
        """Should correctly identify ragged arrays/lists."""
        self.assertTrue(_is_ragged_in_1st_dim_only([ [1], [1, 2] ]),
                        "Ragged nested list not detected!")
        self.assertTrue(_is_ragged_in_1st_dim_only([ np.array([1]), np.array([1, 2]) ]),
                        "Ragged list of arrays not detected!")
        self.assertFalse(_is_ragged_in_1st_dim_only([ [1, 2], [3, 4] ]),
                         "Non-ragged nested list detected incorrectly!")
        self.assertFalse(_is_ragged_in_1st_dim_only(np.array([ [1, 2], [3, 4] ])),
                         "Non-ragged array detected incorrectly!")
        self.assertTrue(_is_ragged_in_1st_dim_only([ [[1]], [[2], [3]] ]),
                        "Ragged nested list not detected even though shape[1:] matches!")
        self.assertFalse(_is_ragged_in_1st_dim_only([ [[1, 2, 3]], [[2]], [[3]] ]),
                         "Ragged nested list detected incorrectly even though shape[1:] don't match!")


if __name__ == "__main__":
    unittest.main()
