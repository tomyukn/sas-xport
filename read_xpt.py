import datetime
import math
import struct
from enum import Enum
from typing import Any, List, NamedTuple, Optional, Tuple, Union


def as_date(x: float) -> datetime.date:
    """数値→日付変換"""
    return datetime.date(1960, 1, 1) + datetime.timedelta(days=x)


def as_int(b: bytes) -> int:
    """バイナリ→整数変換"""
    return int.from_bytes(b, "big")


def as_str(b: bytes) -> str:
    """バイナリ→文字列変換"""
    return b.decode()


def ceil_base(n: int, base: int) -> int:
    """`n`を直近の`base`の倍数に切り上げる"""
    return int(math.ceil(n / base) * base)


def decode_hfp64(data: bytes) -> float:
    """IBM方式の64ビット浮動小数点数を読み込む"""
    n = struct.unpack(">Q", data)[0]
    if n == 0:
        return 0.0
    s = n >> 63 & 0x1
    e = n >> 56 & 0x7F
    f = (n & 0xFFFFFFFFFFFFFF) * pow(2, -56)
    return pow(-1, s) * pow(16, e - 64) * f


class VariableType(Enum):
    Numeric = 1
    Character = 2


class Justify(Enum):
    Left = 0
    Right = 1


class SasFormat(NamedTuple):
    """フォーマット名、インフォーマット名組み立て用"""

    name: bytes
    length: bytes
    decimals: bytes
    justify: Optional[bytes]

    def __str__(self) -> str:
        name = as_str(self.name).strip()
        w = as_int(self.length)
        d = as_int(self.justify) if self.justify is not None else 0

        if name.strip() == "" and w == 0:
            return ""

        format_base = f"{name}{w}."
        return f"{format_base}{d}" if d > 0 else format_base


class Namestr:
    """Namestrレコード（変数情報）"""

    def __init__(self, data: bytes) -> None:
        self.raw_record = data

        self._type = data[0:2]
        self._name_hash = data[2:4]
        self._length = data[4:6]
        self._varnum = data[6:8]
        self._name = data[8:16]
        self._label = data[16:56]
        self._format = SasFormat(data[56:64], data[64:66], data[66:68], data[68:70])
        self._informat = SasFormat(data[72:80], data[80:82], data[82:84], None)
        self._position = data[84:88]

    @property
    def type(self) -> VariableType:
        type_int = as_int(self._type)
        return VariableType(type_int)

    @property
    def length(self) -> int:
        return as_int(self._length)

    @property
    def varnum(self) -> int:
        return as_int(self._varnum)

    @property
    def name(self) -> str:
        return as_str(self._name)

    @property
    def label(self) -> str:
        return as_str(self._label)

    @property
    def format(self) -> SasFormat:
        return self._format

    @property
    def informat(self) -> str:
        return str(self._informat)

    @property
    def position(self) -> int:
        return as_int(self._position)

    def __str__(self) -> str:
        return (
            "Namestr("
            f"type={self.type}, "
            f"length={self.length}, "
            f"varnum={self.varnum}, "
            f"name={self.name}, "
            f"label={self.label}, "
            f"format={self.format}, "
            f"informat={self.informat}, "
            f"position={self.position}"
            ")"
        )


class SasVariable(NamedTuple):
    varnum: int
    name: str
    type: VariableType
    length: int
    label: str
    format: SasFormat
    value: Any
    raw_value: bytes


def read_xpt_1obs(xport_file: str) -> Tuple[List[SasVariable], List[bytes]]:
    records: List[bytes] = []
    namestr_records: List[Namestr] = []
    obs: List[SasVariable] = []

    with open(xport_file, "rb") as xpt:
        # library header recordからnamestr header recordまでの8レコードを読み込む
        for _ in range(8):
            data = xpt.read(80)
            records.append(data)

            if as_str(data).startswith("HEADER RECORD*******MEMBER  HEADER RECORD"):
                # namestrレコードのサイズ
                namestr_record_size = int(as_str(data[74:78]))
            elif as_str(data).startswith("HEADER RECORD*******NAMESTR HEADER RECORD"):
                # 変数の数
                n_vars = int(as_str(data[54:58]))

        # namestrレコード（変数情報）を読み込んで`Namestr`オブジェクトにまとめる
        for _ in range(n_vars):
            data = xpt.read(namestr_record_size)
            namestr_records.append(Namestr(data))
            records.append(data)

        # observation headerまでスキップ
        namestr_length = namestr_record_size * n_vars
        padding = ceil_base(namestr_length, base=80) - namestr_length
        _ = xpt.read(padding)

        # observation headerレコード
        records.append(xpt.read(80))

        # データレコード
        for var in namestr_records:
            value = xpt.read(var.length)

            if var.type == VariableType.Character:
                decoded_value: Union[str, float] = as_str(value)
            elif var.type == VariableType.Numeric:
                if value[0] == 0x2E:
                    decoded_value = "<missing>"
                else:
                    decoded_value = decode_hfp64(value)

            obs.append(
                SasVariable(
                    var.varnum,
                    var.name,
                    var.type,
                    var.length,
                    var.label,
                    var.format,
                    decoded_value,
                    value,
                )
            )

    return (obs, records)


if __name__ == "__main__":
    import argparse

    # コマンドライン引数処理
    parser = argparse.ArgumentParser()
    parser.add_argument("xport_file")
    args = parser.parse_args()

    # ヘッダ、Namestrレコード、データ1オブザベーション分を読み込む
    obs, records = read_xpt_1obs(args.xport_file)

    print("[Header records - Namestr records - Observation header]")
    for record in records:
        print(record)

    print("\n[Observation #1]")
    for var in obs:
        if var.type == VariableType.Character:
            val: Union[str, float] = f"'{var.value}'"
        elif str(var.format).startswith("DATE"):
            val = str(as_date(var.value))
        else:
            val = var.value

        print(f"No.    : {var.varnum}")
        print(f"Name   : '{var.name}'")
        print(f"Label  : '{var.label}'")
        print(f"Type   : {var.type.name}")
        print(f"Length : {var.length}")
        print(f"Format : {str(var.format)}")
        print(f"Value  : {val}")
        print("---")
