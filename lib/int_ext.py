
def ordinal(n):
    if type(n) == str: n = int(n)
    return "%d%s" % (n, "tsnrhtdd"[(n / 10 % 10 != 1) * (n % 10 < 4) * n % 10::4])