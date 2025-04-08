from io import TextIOWrapper

from unityparser import UnityDocument
from unityparser.loader import SmartUnityLoader, UnityLoader
from unityparser.register import UnityScalarRegister
from unityparser.utils import load_all, UNIX_LINE_ENDINGS


def unity_load_yaml(text_io_wrapper: TextIOWrapper, try_preserve_types=False):
    """
    :param text_io_wrapper: Text wrapper of text to parse
    :param try_preserve_types: If true, will deserialize what seems to be int and float types to the same Python
        data types instead of deserializing them all as the string type. When/if this value is later serialized
        back it might be represented differently in some corner cases.
    """
    loader_cls = SmartUnityLoader if try_preserve_types else UnityLoader
    register = UnityScalarRegister()
    with text_io_wrapper as fp:
        loader = loader_cls(fp)
        loader.check_data()
        fp.seek(0)
        version = loader.yaml_version
        tags = loader.non_default_tags
        data = [d for d in load_all(fp, register, loader_cls)]
        # use document line endings if no mixed lien endings found, else default to linux
        line_endings = UNIX_LINE_ENDINGS if isinstance(fp.newlines, tuple) else fp.newlines
    doc = UnityDocument(data, newline=line_endings, file_path=None, register=register, version=version,
                        tags=tags)
    return doc
