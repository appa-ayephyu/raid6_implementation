import string, random, os, os.path, pickle
import sys
import functools
from functools import reduce

# The following list of primitive polynomials are the Conway Polynomials
# from the list at
# http://sporadic.stanford.edu/reference/databases/sage/databases/conway.html and
# http://www.math.rwth-aachen.de/~Frank.Luebeck/data/ConwayPol/index.html

gPrimitivePolys = {}
gPrimitivePolysCondensed = {
    1  : (1,0),
    2  : (2,1,0),
    3  : (3,1,0),
    4  : (4,1,0),
    5  : (5,2,0),
    6  : (6,4,3,1,0),
    7  : (7,1,0),
    8  : (8,4,3,2,0),
    9  : (9,4,0),
    10 : (10,6,5,3,2,1,0),
    11 : (11,2,0),
    12 : (12,7,6,5,3,1,0),
    13 : (13,4,3,1,0),
    14 : (14,7,5,3,0),
    15 : (15,5,4,2,0),
    16 : (16,5,3,2,0),
    17 : (17,3,0),
    18 : (18,12,10,1,0),
    19 : (19,5,2,1,0),
    20 : (20,10,9,7,6,5,4,1,0),
    21 : (21,6,5,2,0),
    22 : (22,12,11,10,9,8,6,5,0),
    23 : (23,5,0),
    24 : (24,16,15,14,13,10,9,7,5,3,0),
    25 : (25,8,6,2,0),
    26 : (26,14,10,8,7,6,4,1,0),
    27 : (27,12,10,9,7,5,3,2,0),
    28 : (28,13,7,6,5,2,0),
    29 : (29,2,0),
    30 : (30,17,16,13,11,7,5,3,2,1,0),
    31 : (31,3,0),
    32 : (32,15,9,7,4,3,0),
    33 : (33,13,12,11,10,8,6,3,0),
    34 : (34,16,15,12,11,8,7,6,5,4,2,1,0),
    35 : (35, 11, 10, 7, 5, 2, 0),
    36 : (36, 23, 22, 20, 19, 17, 14, 13, 8, 6, 5, 1, 0),
    37 : (37, 5, 4, 3, 2, 1, 0),
    38 : (38, 14, 10, 9, 8, 5, 2, 1, 0),
    39 : (39, 15, 12, 11, 10, 9, 7, 6, 5, 2 , 0),
    40 : (40, 23, 21, 18, 16, 15, 13, 12, 8, 5, 3, 1, 0),
    64 : (64,33,30,26,25,24,23,22,21,20,18,13,12,11,10,7,5,4,2,1,0),
    97 : (97,6,0),
    100 : (100,15,0)
    }

for n in gPrimitivePolysCondensed.keys():
    gPrimitivePolys[n] = [0]*(n+1)
    unity = 1
    for index in gPrimitivePolysCondensed[n]:
        gPrimitivePolys[n][index] = unity
    gPrimitivePolys[n].reverse()


if sys.version_info[0] >= 3:
    def long(data):
        "Fake the `long` function since not needed after python 2"
        return data


class FField:
    """
    The FField class implements a finite field calculator.  The
    following functions are provided:

    __init__
    Add
    Subtract
    Multiply
    Inverse
    Divide
    FindDegree
    MultiplyWithoutReducing
    ExtendedEuclid
    FullDivision
    ShowCoefficients
    ShowPolynomial
    GetRandomElement
    ConvertListToElement
    TestFullDivision
    TestInverse

    Most of these methods take integers or longs representing field
    elements as arguments and return integers representing the desired
    field elements as output.  See ffield.fields_doc for an explanation
    of the integer representation of field elements.

    Example of how to use the FField class:

>>> import ffield
>>> F = ffield.FField(5) # create the field GF(2^5)
>>> a = 7 # field elements are denoted as integers from 0 to 2^5-1
>>> b = 15
>>> F.ShowPolynomial(a) # show the polynomial representation of a
'x^2 + x^1 + 1'
>>> F.ShowPolynomial(b)
'x^3 + x^2 + x^1 + 1'
>>> c = F.Multiply(a,b) # multiply a and b modulo the field generator
>>> c
8
>>> F.ShowPolynomial(c)
'x^3'
>>> F.Multiply(c,F.Inverse(a)) == b # verify multiplication works
1
>>> F.Multiply(c,F.Inverse(b)) == a # verify multiplication works
1
>>> d = F.Divide(c,b) # since c = F.Multiply(a,b), d should give a
>>> d
7

    See documentation on the appropriate method for further details.
    """

    def __init__(self,n,gen=0,useLUT=-1):
        """
        This method constructs the field GF(2^p).  It takes one
        required argument, n = p, and two optional arguments, gen,
        representing the coefficients of the generator polynomial
        (of degree n) to use and useLUT describing whether to use
        a lookup table.  If no gen argument is provided, the
        Conway Polynomial of degree n is obtained from the table
        gPrimitivePolys.

        If useLUT = 1 then a lookup table is used for
        computing finite field multiplies and divides.
        If useLUT = 0 then no lookup table is used.
        If useLUT = -1 (the default), then the code
        decides when a lookup table should be used.

        Note that you can look at the generator for the field object
        F by looking at F.generator.
        """

        self.n = n
        if (gen):
            self.generator = gen
        else:
            self.generator = self.ConvertListToElement(gPrimitivePolys[n])


        if (useLUT == 1 or (useLUT == -1 and self.n < 10)): # use lookup table
            self.unity = 1
            self.Inverse = self.DoInverseForSmallField
            self.PrepareLUT()
            self.Multiply = self.LUTMultiply
            self.Divide = self.LUTDivide
            self.Inverse = functools.partial(self.LUTDivide, 1)
        elif (self.n < 15):
            self.unity = 1
            self.Inverse = self.DoInverseForSmallField
            self.Multiply = self.DoMultiply
            self.Divide = self.DoDivide
        else: # Need to use longs for larger fields
            self.unity = long(1)
            self.Inverse = self.DoInverseForBigField
            self.Multiply = lambda a,b: self.DoMultiply(long(a),long(b))
            self.Divide = lambda a,b: self.DoDivide(long(a),long(b))



    def PrepareLUT(self):
        fieldSize = 1 << self.n
        lutName = 'ffield.lut.' + repr(self.n)
        if (os.path.exists(lutName)):
            fd = open(lutName,'rb')
            self.lut = pickle.load(fd)
            fd.close()
        else:
            self.lut = LUT()
            self.lut.mulLUT = list(range(fieldSize))
            self.lut.divLUT = list(range(fieldSize))
            self.lut.mulLUT[0] = [0]*fieldSize
            self.lut.divLUT[0] = ['NaN']*fieldSize
            for i in range(1,fieldSize):
                self.lut.mulLUT[i] = [self.DoMultiply(i,x)
                                      for x in range(fieldSize)]
                self.lut.divLUT[i] = [self.DoDivide(i,x)
                                      for x in range(fieldSize)]
            fd = open(lutName,'wb')
            pickle.dump(self.lut,fd)
            fd.close()


    def LUTMultiply(self,i,j):
        return self.lut.mulLUT[i][j]

    def LUTDivide(self,i,j):
        return self.lut.divLUT[i][j]

    def Add(self,x,y):
        """
        Adds two field elements and returns the result.
        """

        return x ^ y

    def Subtract(self,x,y):
        """
        Subtracts the second argument from the first and returns
        the result.  In fields of characteristic two this is the same
        as the Add method.
        """
        return self.Add(x,y)

    def DoMultiply(self,f,v):
        """
        Multiplies two field elements (modulo the generator
        self.generator) and returns the result.

        See MultiplyWithoutReducing if you don't want multiplication
        modulo self.generator.
        """
        m = self.MultiplyWithoutReducing(f,v)
        return self.FullDivision(m,self.generator,
                                 self.FindDegree(m),self.n)[1]

    def DoInverseForSmallField(self,f):
        """
        Computes the multiplicative inverse of its argument and
        returns the result.
        """
        return self.ExtendedEuclid(1,f,self.generator,
                                   self.FindDegree(f),self.n)[1]

    def DoInverseForBigField(self,f):
        """
        Computes the multiplicative inverse of its argument and
        returns the result.
        """
        return self.ExtendedEuclid(self.unity,long(f),self.generator,
                                   self.FindDegree(long(f)),self.n)[1]

    def DoDivide(self,f,v):
        """
        Divide(f,v) returns f * v^-1.
        """
        return self.DoMultiply(f,self.Inverse(v))

    def FindDegree(self,v):
        """
        Find the degree of the polynomial representing the input field
        element v.  This takes O(degree(v)) operations.

        A faster version requiring only O(log(degree(v)))
        could be written using binary search...
        """

        if (v):
            result = -1
            while(v):
                v = v >> 1
                result = result + 1
            return result
        else:
            return 0

    def MultiplyWithoutReducing(self,f,v):
        """
        Multiplies two field elements and does not take the result
        modulo self.generator.  You probably should not use this
        unless you know what you are doing; look at Multiply instead.

        NOTE: If you are using fields larger than GF(2^15), you should
        make sure that f and v are longs not integers.
        """

        result = 0
        mask = self.unity
        i = 0
        while (i <= self.n):
            if (mask & v):
                result = result ^ f
            f = f << 1
            mask = mask << 1
            i = i + 1
        return result


    def ExtendedEuclid(self,d,a,b,aDegree,bDegree):
        """
        Takes arguments (d,a,b,aDegree,bDegree) where d = gcd(a,b)
        and returns the result of the extended Euclid algorithm
        on (d,a,b).
        """
        if (b == 0):
            return (a,self.unity,0)
        else:
            (floorADivB, aModB) = self.FullDivision(a,b,aDegree,bDegree)
            (d,x,y) = self.ExtendedEuclid(d, b, aModB, bDegree,
                                          self.FindDegree(aModB))
            return (d,y,self.Subtract(x,self.DoMultiply(floorADivB,y)))

    def FullDivision(self,f,v,fDegree,vDegree):
        """
        Takes four arguments, f, v, fDegree, and vDegree where
        fDegree and vDegree are the degrees of the field elements
        f and v represented as a polynomials.
        This method returns the field elements a and b such that

            f(x) = a(x) * v(x) + b(x).

        That is, a is the divisor and b is the remainder, or in
        other words a is like floor(f/v) and b is like f modulo v.
        """

        result = 0
        i = fDegree
        mask = self.unity << i
        while (i >= vDegree):
            if (mask & f):
                result = result ^ (self.unity << (i - vDegree))
                f = self.Subtract(f, v << (i - vDegree))
            i = i - 1
            mask = mask >> self.unity
        return (result,f)


    def ShowCoefficients(self,f):
        """
        Show coefficients of input field element represented as a
        polynomial in decreasing order.
        """

        fDegree = self.n

        result = []
        for i in range(fDegree,-1,-1):
            if ((self.unity << i) & f):
                result.append(1)
            else:
                result.append(0)

        return result

    def ShowPolynomial(self,f):
        """
        Show input field element represented as a polynomial.
        """

        fDegree = self.FindDegree(f)
        result = ''

        if (f == 0):
            return '0'

        for i in range(fDegree,0,-1):
            if ((1 << i) & f):
                result = result + (' x^' + repr(i))
        if (1 & f):
            result = result + ' ' + repr(1)
        return result.strip().replace(' ',' + ')

    def GetRandomElement(self,nonZero=0,maxDegree=None):
        """
        Return an element from the field chosen uniformly at random
        or, if the optional argument nonZero is true, chosen uniformly
        at random from the non-zero elements, or, if the optional argument
        maxDegree is provided, ensure that the result has degree less
        than maxDegree.
        """

        if (None == maxDegree):
            maxDegree = self.n
        if (maxDegree <= 1 and nonZero):
            return 1
        if (maxDegree < 31):
            return random.randint(nonZero != 0,(1<<maxDegree)-1)
        else:
            result = 0
            for i in range(0,maxDegree):
                result = result ^ (random.randint(0,1) << long(i))
            if (nonZero and result == 0):
                return self.GetRandomElement(1)
            else:
                return result



    def ConvertListToElement(self,l):
        """
        This method takes as input a binary list (e.g. [1, 0, 1, 1])
        and converts it to a decimal representation of a field element.
        For example, [1, 0, 1, 1] is mapped to 8 | 2 | 1 = 11.

        Note if the input list is of degree >= to the degree of the
        generator for the field, then you will have to call take the
        result modulo the generator to get a proper element in the
        field.
        """

        temp = map(lambda a, b: a << b, l, range(len(l)-1,-1,-1))
        return reduce(lambda a, b: a | b, temp)

    def TestFullDivision(self):
        """
        Test the FullDivision function by generating random polynomials
        a(x) and b(x) and checking whether (c,d) == FullDivision(a,b)
        satsifies b*c + d == a
        """
        f = 0

        a = self.GetRandomElement(nonZero=1)
        b = self.GetRandomElement(nonZero=1)
        aDegree = self.FindDegree(a)
        bDegree = self.FindDegree(b)

        (c,d) = self.FullDivision(a,b,aDegree,bDegree)
        recon = self.Add(d, self.Multiply(c,b))
        assert (recon == a), ('TestFullDivision failed: a='
                              + repr(a) + ', b=' + repr(b) + ', c='
                              + repr(c) + ', d=' + repr(d) + ', recon=', recon)

    def TestInverse(self):
        """
        This function tests the Inverse function by generating
        a random non-zero polynomials a(x) and checking if
        a * Inverse(a) == 1.
        """

        a = self.GetRandomElement(nonZero=1)
        aInv = self.Inverse(a)
        prod = self.Multiply(a,aInv)
        assert 1 == prod, ('TestInverse failed:' + 'a=' + repr(a) + ', aInv='
                           + repr(aInv) + ', prod=' + repr(prod),
                           'gen=' + repr(self.generator))

class LUT:
    """
    Lookup table used to speed up some finite field operations.
    """
    pass


class FElement:
    """
    This class provides field elements which overload the
    +,-,*,%,//,/ operators to be the appropriate field operation.
    Note that before creating FElement objects you must first
    create an FField object.  For example,

>>> import ffield
>>> F = ffield.FField(5)
>>> e1 = ffield.FElement(F,7)
>>> e1
x^2 + x^1 + 1
>>> e2 = ffield.FElement(F,19)
>>> e2
x^4 + x^1 + 1
>>> e3 = e1 + e2
>>> e3
x^4 + x^2
>>> e4 = e3 / e2
>>> e4
x^4 + x^3
>>> e4 * e2 == (e3)
1

    """

    def __init__(self,field,e):
        """
        The constructor takes two arguments, field, and e where
        field is an FField object and e is an integer representing
        an element in FField.

        The result is a new FElement instance.
        """
        self.f = e
        self.field = field

    def __add__(self,other):
        assert self.field == other.field
        return FElement(self.field,self.field.Add(self.f,other.f))

    def __mul__(self,other):
        assert self.field == other.field
        return FElement(self.field,self.field.Multiply(self.f,other.f))

    def __mod__(self,o):
        assert self.field == o.field
        return FElement(self.field,
                        self.field.FullDivision(self.f,o.f,
                                                self.field.FindDegree(self.f),
                                                self.field.FindDegree(o.f))[1])

    def __floordiv__(self,o):
        assert self.field == o.field
        return FElement(self.field,
                        self.field.FullDivision(self.f,o.f,
                                                self.field.FindDegree(self.f),
                                                self.field.FindDegree(o.f))[0])

    def __truediv__(self,other):
        assert self.field == other.field
        return FElement(self.field,self.field.Divide(self.f,other.f))

    def __div__(self, *args, **kwargs):
        "syntatic sugar for calling self.__truediv__(*args, **kwargs)"
        return self.__truediv__(*args, **kwargs)

    def __str__(self):
        return self.field.ShowPolynomial(self.f)

    def __repr__(self):
        return self.__str__()

    def __eq__(self,other):
        assert self.field == other.field
        return self.f == other.f

def FullTest(testsPerField=10,sizeList=None):
    """
    This function runs TestInverse and TestFullDivision for testsPerField
    random field elements for each field size in sizeList.  For example,
    if sizeList = (1,5,7), then thests are run on GF(2), GF(2^5), and
    GF(2^7).  If sizeList == None (which is the default), then every
    field is tested.
    """

    if (None == sizeList):
        sizeList = gPrimitivePolys.keys()
    for i in sizeList:
        F = FField(i)
        for j in range(testsPerField):
            F.TestInverse()
            F.TestFullDivision()


def _test():
    import doctest, ffield
    return doctest.testmod(ffield)

if __name__ == "__main__":
    print('Starting automated tests (this may take a while)')
    _test()
    print('Tests finished.')
