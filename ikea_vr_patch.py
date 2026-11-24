import sys, os, re, struct, hashlib


def read_unreal_str(buf, pos):
    n = struct.unpack_from("<i", buf, pos)[0]
    pos += 4
    if n < 0:
        return buf[pos : pos - 2 * n].decode("utf-16-le").rstrip("\0"), pos - 2 * n
    return buf[pos : pos + n].decode("latin-1").rstrip("\0"), pos + n


def write_unreal_str(text):
    return struct.pack("<i", len(text) + 1) + text.encode() + b"\0"


def extract(pak, asset_path):
    f = open(pak, "rb")
    f.seek(-36, 2)
    idxoffset, idxsize = struct.unpack("<qq", f.read(16))
    f.seek(idxoffset)
    idx = f.read(idxsize)
    mnt, pos = read_unreal_str(idx, 0)
    nfiles = struct.unpack_from("<I", idx, pos)[0]
    pos += 4
    for file in range(nfiles):
        name, pos = read_unreal_str(idx, pos)
        off, size = struct.unpack_from("<qq", idx, pos)
        pos += 53
        if name != asset_path:
            continue
        f.seek(off + 53)
        return f.read(size), mnt
    sys.exit(f"couldnt find {asset_path} in pak")


def write_pak(path, mnt, name, data):
    sha = hashlib.sha1(data).digest()
    entry = struct.pack("<qqqI", 0, len(data), len(data), 0) + sha + b"\0\0\0\0\0"
    idx = write_unreal_str(mnt) + struct.pack("<I", 1) + write_unreal_str(name) + entry
    body = entry + data
    footer = (
        struct.pack("<IIqq", 0x5A6F12E1, 3, len(body), len(idx))
        + hashlib.sha1(idx).digest()
    )
    with open(path, "wb") as f:
        f.write(body + idx + footer)


if len(sys.argv) < 2:
    sys.exit("usage: python ikea_vr_patch.py <path to IKEAVR2-WindowsNoEditor.pak>")
pak = sys.argv[1]
if not os.path.isfile(pak):
    sys.exit("no such file: " + pak)

data, mnt = extract(pak, "IKEAVR2/Content/GUI/FirstScreen.uasset")
hits = [m.start(1) for m in re.finditer(rb"\x1c....\x24(\x00)\x16", data, re.S)]
if len(hits) != 1:
    sys.exit(f"found {len(hits)} matches instead of 1?? wtf")
_data = bytearray(data)
_data[hits[0]] = 1
out = os.path.join(
    os.path.dirname(os.path.abspath(pak)), "IKEAVR2-WindowsNoEditor_P.pak"
)
write_pak(out, mnt, "IKEAVR2/Content/GUI/FirstScreen.uasset", bytes(_data))
print(f"done: wrote patched pak file at: {out}")
