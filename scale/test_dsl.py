import unittest, tokenize
from scale.dsl import *

BOM = '\xef\xbb\xbf'
original = u'\u6789'
encoded  = "u'%s'" % original.encode('utf8')    # utf8-encoded source
markers = ["# coding: utf-8\n", "# -*- coding=utf8 -*-\n"]


class PEP263_Encoding_Tests(unittest.TestCase):

    def checkDecode(self, src):
        result = detokenize(tokenize_string(src))
        assert isinstance(result, unicode)
        self.assertEqual(eval(result.splitlines()[-1]), original)

    def checkFail(self, src):
        result = detokenize(tokenize_string(src))
        assert isinstance(result, str), result.encode('utf8')
        try:
            self.assertNotEqual(eval(result), original)
        except SyntaxError:
            pass
        
    def testBOM(self):
        self.checkDecode(BOM+encoded)       # Decode text on same line as BOM       
        self.checkDecode(BOM+'\n'+encoded)  # Decode text on line after BOM

        # But if the BOM's not on the first line, we get crap:
        self.checkFail('\n'+BOM+encoded)

    def testUnicode(self):
        self.checkDecode('u"'+original+'"')
        self.checkDecode('# coding: latin-1\nu"'+original+'"')

    def testFalseCoding(self):
        self.checkFail('coding=utf8\n'+encoded)
        self.checkFail('"""coding=utf8"""\n#coding: utf8\n'+encoded)



    def testCoding(self):
        for prefix in '', '\n', BOM, BOM+'\n':
            for marker in markers:
                self.checkDecode(prefix+marker+encoded)
                self.checkFail('\n\n'+marker+encoded)

    def testConflict(self):
        for val,pos  in [ ("# coding: latin-1\n", (1,10)), ]:
            try:
                detokenize(tokenize_string(BOM+val))
            except tokenize.TokenError, v:
                assert v.args[1]==pos, (
                    "Error position should be", pos, v.args[1]
                )
            else:
                raise AssertionError("Should've detected BOM/coding conflict")



class BlockParsingTests(unittest.TestCase):

    def checkError(self,what,where,src):
        try:
            parse_block(tokenize_string(src))
        except TokenError,v:
            self.assertEqual(v.args, (what,where))
        else:
            raise AssertionError("Should've got a TokenError for "+repr(src))

    def testSimple(self):
        self.checkError('EOF in multi-line statement', (2, 0),"(1+1")
        self.checkError('Unmatched ]',(1,4),"(1+2]")
        self.checkError('Unexpected indent',(1,0), "   1+2")
        self.checkError('unindent does not match any outer indentation level',
            (3, 2), "if foo:\n"
                     "    bar\n"
                     "  baz\n")




def doctest_suite():
    import doctest
    return doctest.DocFileSuite(
        'dsl.txt', optionflags=doctest.ELLIPSIS, package='scale',
    )

def test_suite():
    import unittest
    return unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromName(__name__),
        doctest_suite(),
    ])





























