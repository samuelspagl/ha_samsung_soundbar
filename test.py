class Stuff:
    def __init__(self, a: int):
        self.__a = a

    def set_a(self, new_a: int):
        self.__a = new_a

    @property
    def a(self):
        return self.__a


class Stuff2:
    def __init__(self, a: int):
        self.stuff = Stuff(a)


    def set_a(self, a):
        self.stuff.set_a(a)

    @property
    def a(self):
        return self.stuff.a

hal = Stuff(3)
print(hal.a)
hal.set_a(5)
print(hal.a)
print()
print()
has = Stuff2(3)
print(has.a)
print(has.stuff.set_a(5))
print(has.a)
print(has.set_a(10))
print(has.a)