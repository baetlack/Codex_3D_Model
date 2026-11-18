"""Read the cell values of the archived BIFF8 equipment ledger."""
from pathlib import Path
import struct


def workbook_stream(path):
    data = Path(path).read_bytes()
    if data[:8] != bytes.fromhex('D0CF11E0A1B11AE1'):
        raise ValueError('Expected an OLE XLS workbook')
    sector_size = 1 << struct.unpack_from('<H', data, 30)[0]
    count, directory = struct.unpack_from('<II', data, 44)
    first_difat, difat_count = struct.unpack_from('<II', data, 68)

    def sector(index):
        start = (index + 1) * sector_size
        return data[start:start + sector_size]

    sector_words = struct.Struct(f'<{sector_size // 4}I')
    fat_sectors = list(struct.unpack_from('<109I', data, 76))
    for _ in range(difat_count):
        words = sector_words.unpack(sector(first_difat))
        fat_sectors.extend(words[:-1])
        first_difat = words[-1]
    fat = [word for index in fat_sectors[:count] for word in sector_words.unpack(sector(index))]

    def chain(index):
        seen = set()
        while index < 0xFFFFFFFA:
            if index in seen:
                raise ValueError('Cyclic XLS stream')
            seen.add(index)
            yield sector(index)
            index = fat[index]

    entries = b''.join(chain(directory))
    for start in range(0, len(entries), 128):
        item = entries[start:start + 128]
        length = struct.unpack_from('<H', item, 64)[0]
        name = item[:max(0, length - 2)].decode('utf-16le')
        if name in {'Workbook', 'Book'}:
            first, size = struct.unpack_from('<IQ', item, 116)
            if size < 4096:
                raise ValueError('Unsupported miniature Workbook stream')
            return b''.join(chain(first))[:size]
    raise ValueError('Workbook stream missing')


def records(stream, offset=0):
    while offset + 4 <= len(stream):
        kind, size = struct.unpack_from('<HH', stream, offset)
        offset += 4
        yield kind, stream[offset:offset + size]
        offset += size
        if kind == 0x000A:
            return


class StringTable:
    def __init__(self, chunks):
        self.chunks = iter(chunks)
        self.current = next(self.chunks)
        self.offset = 8

    def advance(self):
        self.current = next(self.chunks)
        self.offset = 0

    def read(self, size):
        value = bytearray()
        while size:
            if self.offset == len(self.current):
                self.advance()
            take = min(size, len(self.current) - self.offset)
            value.extend(self.current[self.offset:self.offset + take])
            self.offset += take
            size -= take
        return bytes(value)

    def string(self):
        length, flags = struct.unpack('<HB', self.read(3))
        runs = int.from_bytes(self.read(2), 'little') if flags & 8 else 0
        extra = int.from_bytes(self.read(4), 'little') if flags & 4 else 0
        wide = flags & 1
        value = []
        while length:
            if self.offset == len(self.current):
                self.advance()
                wide = self.read(1)[0] & 1
            width = 1 + wide
            count = min(length, (len(self.current) - self.offset) // width)
            if not count:
                raise ValueError('Invalid BIFF8 character continuation')
            value.append(self.read(count * width).decode('utf-16le' if wide else 'latin1'))
            length -= count
        self.read(4 * runs + extra)
        return ''.join(value)


def decode_rk(value):
    if value & 2:
        number = struct.unpack('<i', struct.pack('<I', value))[0] >> 2
    else:
        number = struct.unpack('<d', struct.pack('<II', 0, value & ~3))[0]
    return number / 100 if value & 1 else number


def read_xls(path):
    stream = workbook_stream(path)
    globals_ = list(records(stream))
    sheets = {}
    strings = []
    for index, (kind, data) in enumerate(globals_):
        if kind == 0x0085 and data[5] == 0:
            offset, _, _, length, flags = struct.unpack_from('<IBBBB', data)
            sheets[data[8:8 + length * (1 + (flags & 1))].decode(
                'utf-16le' if flags & 1 else 'latin1')] = offset
        elif kind == 0x00FC:
            chunks = [data]
            for following_kind, following in globals_[index + 1:]:
                if following_kind != 0x003C:
                    break
                chunks.append(following)
            table = StringTable(chunks)
            strings = [table.string() for _ in range(struct.unpack_from('<I', data, 4)[0])]
    result = {}
    for name, offset in sheets.items():
        cells = {}
        for kind, data in records(stream, offset):
            if kind in {0x00FD, 0x0203, 0x027E, 0x00BD, 0x0006}:
                row, col = struct.unpack_from('<HH', data)
                if kind == 0x00FD:
                    cells[row, col] = strings[struct.unpack_from('<I', data, 6)[0]]
                elif kind == 0x0203 or (kind == 0x0006 and data[12:14] != b'\xff\xff'):
                    cells[row, col] = struct.unpack_from('<d', data, 6)[0]
                elif kind == 0x027E:
                    cells[row, col] = decode_rk(struct.unpack_from('<I', data, 6)[0])
                elif kind == 0x00BD:
                    for i in range((len(data) - 6) // 6):
                        cells[row, col + i] = decode_rk(struct.unpack_from('<I', data, 6 + i * 6)[0])
        result[name] = cells
    return result


if __name__ == '__main__':
    import sys

    for sheet, cells in read_xls(sys.argv[1]).items():
        print(sheet, len(cells))
        for row in sorted({row for row, _ in cells}):
            print(row + 1, ' | '.join(f'{col + 1}:{v}' for (r, col), v in sorted(cells.items()) if r == row))
