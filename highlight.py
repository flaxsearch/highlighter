# Copyright (c) 2014 Lemur Consulting Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re
import types
import snowballstemmer

WINDOW = 50   # arrived at through trial and error

# chunks are tags, IP addresses, SSNs, words and punctuation, with trailing spaces
chunk_re = re.compile(r'<\w+[^>]*>\s*|</\w+>\s*|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s*|\d{3}-\d{2}-\d{4}\s*|[\w\'\-]+\s*|[^\w\'\-\s]+\s*')
query_re = re.compile(r'"[^"]+"|[\w\'\-]+')


class NoStem:
    """Stemmer class which does nothing.
    """
    def stemWord(s):
        return s


class Highlighter:

    def __init__(self, language=None):
        """Create a new highlighter for the specified language.
        
        """
        if language:
            self.stem = snowballstemmer.stemmer(language)
        else:
            self.stem = NoStem()

    def makeSample(self, text, query, maxlen=100, hl=('<b>', '</b>')):
        """Make a context-sensitive sample with optional highlights
        
        `text` is the source text to summarise.
        `query` is an iterable of normalised query terms, or matcher function objects
        `maxlen` is the maximum length of the generated summary.
        `maxwords` is the maximum number of words in the generated summary.
        `hl` is a pair of strings to insert around highlighted terms, e.g. ('<b>', '</b>')
        """
        if isinstance (text, unicode):
            text = text.encode('utf-8')
        
        words = [w for w in chunk_re.findall(text) if w[0] != '<']
        lenwords = len(words)
        terms = [self._normalise_text(w) for w in words]
        
        if lenwords == 0: return text
    
        scores = [0] * lenwords
        highlight = [False] * lenwords    
    
        # find query words/phrases, and mark
        for n in xrange(lenwords):
            for q in query:
                try:
                    for offset, term in enumerate(q):
                        if isinstance(term, types.FunctionType) or isinstance(term, types.LambdaType):
                            match = term(terms[n+offset])
                        else:
                            match = terms[n+offset] == term
                        if not match:
                            raise IndexError
                
                    # match found - add scores
                    for offset, term in enumerate(q):
                        scores[n+offset] += WINDOW 
                        highlight[n+offset] = True
                    
                    # scores taper in either direction
                    for w in xrange(1, WINDOW):
                        l = n - w
                        if l < 0: break
                        scores[l] += WINDOW - w
                        
                    for w in xrange(1, WINDOW):
                        r = n + offset + w
                        if r == lenwords: break
                        scores[r] += WINDOW - w
                    
                    break  # go on to next word
                
                except IndexError:
                    pass
        
        # flatten scoring loop
        scoreboard = {}
        for n in xrange(lenwords):
            scoreboard.setdefault(scores[n], []).append(n)
    
        # select words, highest scores first
        selected = [False] * lenwords
        charlen = 0
        try:
            for s in xrange(max(scores), -1, -1):
                if scoreboard.has_key(s):
                    for n in scoreboard[s]:
                        charlen += len(words[n]) + 1
                        if charlen >= maxlen:
                            raise StopIteration
                        selected[n] = True
        
        except StopIteration:
            pass
    
        # create sample
        sample = []
        in_phrase = False
        for n in xrange(lenwords):
            if selected[n]:
#                if in_phrase and word_re.match(words[n]):
#                    sample.append(' ')
                in_phrase = True
                if highlight[n]:
                    sample.append(hl[0])
                    sample.append(words[n])
                    sample.append(hl[1])
                else:
                    sample.append(words[n])
                
            elif in_phrase:
                sample.append('... ')
                in_phrase = False
    
        return ''.join(sample)

    def highlight(self, text, query, hl=('<b>', '</b>'), no_tags=True):
        """
        Add highlights (string prefix/postfix) to a string.
        
        `text` is the source to highlight.
        `query` is an iterable of normalised query terms, or matcher function objects
        `hl` is a pair of highlight strings, e.g. ('<i>', '</i>')
        `no_tags` strips HTML markout iff True
        """
        if isinstance (text, unicode):
            text = text.encode('utf-8')

        words = chunk_re.findall(text)
        if no_tags:
            words = [w for w in words if w[0] != '<']
        lenwords = len(words)
        terms = [self._normalise_text(w) for w in words]

        highlight = [False] * lenwords    
    
        # find query words/phrases, and mark
        for n in xrange(lenwords):
            for q in query:
                try:
                    for offset, term in enumerate(q):
                        # term could be a string or a function f(x) returning true iff f matches x
                        if isinstance(term, types.FunctionType) or isinstance(term, types.LambdaType):
                            match = term(terms[n+offset])
                        else:
                            match = terms[n+offset] == term
                        if not match:
                            raise IndexError    # could also be raised by falling off end
                    
                    for offset, term in enumerate(q):
                        highlight[n+offset] = True

                except IndexError:
                    pass

        sample = []
        for n in xrange(lenwords):
            if highlight[n]:
                sample.append(hl[0])
                sample.append(words[n])
                sample.append(hl[1])
            else:
                sample.append(words[n])

        return ''.join(sample)

    
    def _normalise_text(self, term):
        # remove trailing spaces from words, and stem
        return self.stem.stemWord(term.rstrip().lower())    
    
    def make_hl_terms(self, q):
        """Produce terms for highlighting etc.
        """
        def _normalise(term):
            if term[0] == '"' and term[-1] == '"':
                term = term[1:-1]
            
            return [self.stem.stemWord(x) for x in term.lower().split()]
                
        return [_normalise(r) for r in query_re.findall(q)]

if __name__ == '__main__':    
    with open('sampledoc.txt') as f:
        text = f.read()
        hl = Highlighter('porter')
        print hl.makeSample(text, hl.make_hl_terms('newfoundland'), 500)

