from time import perf_counter_ns


class Timeit:
    def __init__(self):
        self.start = perf_counter_ns()

    def get_ns(self) -> int:
        return perf_counter_ns() - self.start

    def get_sec(self) -> float:
        return self.get_ns() / 1e9

    def __str__(self):
        return str(self.get_sec())

    def __format__(self, format_spec):
        return format(self.get_sec(), format_spec)

    def __repr__(self):
        return f"({self:.2f} sec)"
