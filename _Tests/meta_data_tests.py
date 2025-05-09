from unittest import TestCase, main as ut_main

from Utility.meta_data import MetaDataHandler, _get_meta_guid, get_meta_by_name, get_meta_dict_by_name_set, \
    get_meta_by_name_set, get_meta_by_guid, get_meta_by_guid_set, get_meta_dict_by_guid_set
from Utility.utility import normalize_str


class BaseMetaDataTest(TestCase):
    def __init__(self, *args):
        super().__init__(*args)

        self.handler = MetaDataHandler()
        self.names_list = ["I2Languages", "enemies", "items", "UI", "LaborratoryTexturePacked"]
        guids_list = [_get_meta_guid(self.handler.get_path_by_name(name)) for name in self.names_list]
        self.guids_list = [guid[0] for guid in guids_list if guid]


class MetaDataLoad(BaseMetaDataTest):

    def test_meta_data_loaded(self):
        self.assertIsNotNone(self.handler)

    def test_parsed_every_guid(self):
        self.assertEqual(len(self.names_list), len(self.guids_list))

    def test_get_by_name(self):
        for name in self.names_list:
            self.assertIsNotNone(self.handler.get_path_by_name(name))

    def test_get_by_name_no_meta(self):
        for name in self.names_list:
            self.assertIsNotNone(self.handler.get_path_by_name_no_meta(name))

    def test_get_by_guid(self):
        for guid in self.guids_list:
            self.assertIsNotNone(guid)
            self.assertIsNotNone(self.handler.get_path_by_guid(guid))

    def test_filter_assets(self):
        search_list = ["MasterAudio", "DynamicSoundGroup", "ProjectContext"]

        def flt(tuple_s_p):
            s, _ = tuple_s_p
            return any(normalize_str(search) in normalize_str(s) for search in search_list)

        self.assertGreaterEqual(len(self.handler.filter_paths(flt)), 2)


class MetaDataGet(BaseMetaDataTest):

    def __init__(self, *args):
        super().__init__(*args)

        self.handler = MetaDataHandler()
        self.names_list = self.names_list[1:]
        self.guids_list = self.guids_list[1:]

    def test_get_by_name(self):
        for name in self.names_list:
            self.assertIsNotNone(get_meta_by_name(name))

        names_set = set(self.names_list)
        data_set = get_meta_by_name_set(names_set)
        data_dict = get_meta_dict_by_name_set(names_set)

        self.assertEqual(len(data_set), len(data_dict))
        self.assertEqual(data_set, set(data_dict.values()))

        self.assertEqual(set(data_dict.keys()), names_set)

    def test_get_by_guid(self):
        for guid in self.guids_list:
            self.assertIsNotNone(get_meta_by_guid(guid))

        guids_set = set(self.guids_list)
        data_set = get_meta_by_guid_set(guids_set)
        data_dict = get_meta_dict_by_guid_set(guids_set)

        self.assertEqual(len(data_set), len(data_dict))
        self.assertEqual(data_set, set(data_dict.values()))

        self.assertEqual(set(data_dict.keys()), guids_set)

    def test_init_sprites_animations(self):
        names_set = set(self.names_list)
        data_set = get_meta_by_name_set(names_set)

        for data, sp_i, an_i in zip(data_set, [10] * 4, [5, 5, 5, 0]):
            data.init_sprites()
            data.init_animations()

            self.assertGreaterEqual(sum(map(lambda x: x.sprite is not None, data.data_name.values())), sp_i,
                                    f"Failed on {data.real_name}")
            self.assertGreaterEqual(sum(map(lambda x: x.animation is not None, data.data_name.values())), an_i,
                                    f"Failed on {data.real_name}")


if __name__ == "__main__":
    ut_main()
