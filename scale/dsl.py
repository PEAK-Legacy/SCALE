"""Parsing tools for SCALE and other Python-like Domain-Specific Languages"""

__all__ = [
    "tokenize_string", "tokenize_stream", "tokenize_file", "detokenize",
    "parse_block", "flatten_block", "strip_ws", "TokenError", "SUBEXPR",
    "flatten_stmt", "partition", "rpartition",
]

from StringIO import StringIO
from tokenize import generate_tokens, NL, NEWLINE, ENDMARKER, INDENT, DEDENT
from tokenize import COMMENT, NAME, NUMBER, STRING, ERRORTOKEN, OP, TokenError
from tokenize import tok_name
import re

WHITESPACE = dict.fromkeys([NL,NEWLINE,ENDMARKER,INDENT,DEDENT,COMMENT])
OPEN_PARENS = dict.fromkeys('{[(')
CLOSE_PARENS = {'}':'{', ')':'(', ']':'['}
SUBEXPR = 9999
tok_name[SUBEXPR] = "SUBEXPR"

BOM = '\xef\xbb\xbf'
ENCODING_LINE = re.compile('('+BOM+')|\s*(#.*)?$').match
FIND_ENCODING = re.compile('coding[:=]\s*([-\w.]+)').search

def tokenize_string(text):
    """Yield the tokens of `text`

    `text` may be a string or unicode object.  If it's a string, PEP 263
    source encoding comments/BOM markers will be recognized.
    """
    return tokenize_stream(StringIO(text))

def tokenize_file(filename):
    """Yield the tokens contained in the file named by `filename`

    PEP 263 source encoding comments and BOM markers will be recognized.
    """
    return tokenize_stream(open(filename,'rU'))



def tokenize_stream(file):
    """Yield the tokens contained in an iterable of lines

    This function assumes only that `file` is an iterable yielding string or
    Unicode objects.  If the first two lines are strings, they're checked for
    PEP 263 source encoding comments, and the first is checked for a UTF-8 BOM
    marker.  If an encoding or BOM is found, the remainder of the stream is
    decoded as unicode.  (Lines prior to the declaration line are not decoded.)
    """
    def reader(f):
        lno, encoding, bom = 1, None, False
        for line in f:
            if isinstance(line, unicode) or not ENCODING_LINE(line):
                yield line  
                break
            if lno==1 and line.startswith(BOM):
                bom = True
                encoding = "utf8"
                line = line[len(BOM):].decode(encoding)
            if line.find('coding')>=0:
                match = FIND_ENCODING(line)
                if match:
                    encoding = match.group(1)
                    if bom and encoding.lower() not in ('utf8', 'utf-8'):
                        raise TokenError(
                            ("UTF-8 BOM, but %r encoding requested" %encoding),
                            (lno,match.start(1))
                        )
            yield line
            lno += 1
            if encoding or lno>2:
                break
        if encoding:
            from codecs import getreader
            f = getreader(encoding)(f)

        for line in f:
            yield line
        yield ''
    return generate_tokens(reader(file).next)

def parse_block(tokens):
    """Turn an iterable of tokens into a tree of statements

    Returns a `block`, where a block is a list of (`statement`,`block`) tuples.
    Each `statement` is a list of the tokens composing a logical source line,
    and each `block` represents the block indented beneath `statement`, if any.
    Each nested `block` is in turn a list of (`statement`,`block`) tuples.  If
    a given statement has no nested block beneath it, its `block` is an empty
    list.
    """
    scopes = []
    parens = []
    indents = [0]
    output = scope = []
    stmt = []

    for tok, val, start, end, line in tokens:

        if tok==DEDENT or tok==ENDMARKER:   # exiting a scope
            if tok==DEDENT:
                if len(line[:start[1]].expandtabs()) not in indents:
                    raise TokenError(
                        "unindent does not match any outer indentation level",
                        start
                    )
                indents.pop()
            elif parens:
                raise TokenError(
                    "Unclosed parentheses %r" % (tuple(parens[::-1]),), start
                )

            if stmt:
                scope.append((stmt,[]))
                stmt = []
            if scopes:
                assert tok != ENDMARKER, "Missing DEDENT tokens"
                scope = scopes.pop()
            else:
                assert tok == ENDMARKER, "Extra DEDENT tokens"
                return output

        elif tok==INDENT:
            if not scope:   # no statement that this indent is under!
                raise TokenError("Unexpected indent", start)
            scopes.append(scope)
            indents.append(len(val.expandtabs()))
            scope = scope[-1][1]    # fill in block under statement

        else:
            if tok==OP and val in OPEN_PARENS:
                parens.append(val)
                scopes.append(stmt)
                subexpr = []
                stmt.append((SUBEXPR, subexpr, start, end, line))
                stmt = subexpr

            stmt.append((tok, val, start, end, line))

            if tok==OP and val in CLOSE_PARENS:
                if not parens or parens.pop()<>CLOSE_PARENS[val]:
                    raise TokenError("Unmatched "+val, start)
                stmt = scopes.pop()

            elif tok==NEWLINE:
                scope.append((stmt,[]))
                stmt = []

    assert False, "Token stream didn't have an ENDMARKER"














def flatten_block(block):
    """Yield the tokens composing `block`"""
    for stmt,subblock in block:
        for tok in flatten_stmt(stmt):
            yield tok
        if subblock:
            for tok in flatten_block(subblock):
                yield tok

def flatten_stmt(statement):
    """Yield the tokens composing `statement`"""
    for tok in statement:
        if tok[0]==SUBEXPR:
            for tok in flatten_stmt(tok[1]):
                yield tok
        else:
            yield tok
                
def strip_ws(tokens):
    """Yield non-whitespace tokens from `tokens`"""
    for tok in tokens:
        if tok[0] not in WHITESPACE:
            yield tok


















def partition(tokens, sep):
    """Split `tokens` into (`before`, `sep`, `after`) tuple at first `sep`"""
    before = []
    after = iter(tokens)
    idx = int(not isinstance(sep,int))   # int matches tok[0], str -> tok[1]
    for tok in after:
        if tok[idx]==sep:
            return before,[tok],after
        before.append(tok)
    else:
        return before,[],after

def rpartition(tokens,sep):
    """Split `tokens` into (`before`, `sep`, `after`) tuple at last `sep`"""
    b,s,a = partition(list(tokens)[::-1], sep)
    b.reverse()
    return list(a)[::-1],s,b
























def detokenize(tokens, indent=0):
    """Convert `tokens` iterable back to a string."""
    out = []; add = out.append
    lr,lc,last = 0,0,''
    baseindent = None
    for tok, val, (sr,sc), (er,ec), line in flatten_stmt(tokens):
        # Insert trailing line continuation and blanks for skipped lines
        lr = lr or sr   # first line of input is first line of output
        if sr>lr:
            if last:
                if len(last)>lc:
                    add(last[lc:])
                lr+=1
            if sr>lr:
                add(' '*indent + '\\\n'*(sr-lr))    # blank continuation lines
            lc = 0

        # Re-indent first token on line
        if lc==0:
            if tok==INDENT:
                continue  # we want to dedent first actual token
            else:
                curindent = len(line[:sc].expandtabs())
                if baseindent is None and tok not in WHITESPACE:
                    baseindent = curindent
                elif baseindent is not None and curindent>=baseindent:
                    add(' ' * (curindent-baseindent))
                if indent and tok not in (DEDENT, ENDMARKER, NL, NEWLINE):
                    add(' ' * indent)

        # Not at start of line, handle intraline whitespace by retaining it
        elif sc>lc:
            add(line[lc:sc])

        if val:
            add(val)

        lr,lc,last = er,ec,line

    return ''.join(out)

