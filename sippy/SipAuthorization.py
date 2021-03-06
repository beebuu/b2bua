# Copyright (c) 2003-2005 Maxim Sobolev. All rights reserved.
# Copyright (c) 2006-2014 Sippy Software, Inc. All rights reserved.
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation and/or
# other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from sippy.SipGenericHF import SipGenericHF
from hashlib import md5
from time import time
from binascii import hexlify

class SipAuthorization(SipGenericHF):
    hf_names = ('authorization',)
    username = None
    uri = None
    realm = None
    nonce = None
    response = None
    qop = None
    cnonce = None
    nc = None
    otherparams = None

    def __init__(self, body = None, username = None, uri = None, realm = None, nonce = None, response = None, \
                 password = None, method = None, cself = None):
        SipGenericHF.__init__(self, body)
        if body != None:
            return
        self.parsed = True
        if cself != None:
            self.username = cself.username
            self.uri = cself.uri
            self.realm = cself.realm
            self.nonce = cself.nonce
            self.response = cself.response
            self.qop = cself.qop
            self.cnonce = cself.cnonce
            self.nc = cself.nc
            self.otherparams = cself.otherparams[:]
            return
        self.username = username
        self.uri = uri
        self.realm = realm
        self.nonce = nonce
        if response == None:
            HA1 = DigestCalcHA1('md5', username, realm, password, nonce, '')
            self.response = DigestCalcResponse(HA1, nonce, 0, '', '', method, uri, '')
        else:
            self.response = response
        self.otherparams = []

    def parse(self):
        self.otherparams = []
        for name, value in [x.strip(', ').split('=', 1) for x in self.body.split(' ', 1)[1].split(',')]:
            ci_name = name.lower()
            if ci_name == 'username':
                self.username = value.strip('"')
            elif ci_name == 'uri':
                self.uri = value.strip('"')
            elif ci_name == 'realm':
                self.realm = value.strip('"')
            elif ci_name == 'nonce':
                self.nonce = value.strip('"')
            elif ci_name == 'response':
                self.response = value.strip('"')
            elif ci_name == 'qop':
                self.qop = value.strip('"')
            elif ci_name == 'cnonce':
                self.cnonce = value.strip('"')
            elif ci_name == 'nc':
                self.nc = value.strip('"')
            else:
                self.otherparams.append((name, value))
        self.parsed = True

    def __str__(self):
        if not self.parsed:
            return self.body
        rval = 'Digest username="%s",realm="%s",nonce="%s",uri="%s",response="%s"' % \
               (self.username, self.realm, self.nonce, self.uri, self.response)
        if self.qop != None:
            rval += ',nc="%s",cnonce="%s",qop=%s' % (self.nc, self.cnonce, \
              self.qop)
        for param in self.otherparams:
            rval += ',%s=%s' % param
        return rval

    def getCopy(self):
        if not self.parsed:
            return self.__class__(self.body)
        return self.__class__(cself = self)

    def verify(self, password, method):
        if not self.parsed:
            self.parse()
        return self.verifyHA1(DigestCalcHA1('md5', self.username, self.realm, password, self.nonce, ''), method)

    def verifyHA1(self, HA1, method):
        if not self.parsed:
            self.parse()
        response = DigestCalcResponse(HA1, self.nonce, self.nc, \
          self.cnonce, self.qop, method, self.uri, '')
        return response == self.response

    def getCanName(self, name, compact = False):
        return 'Authorization'

    def hasValidNonce(self, timeout = 300):
        if self.nonce == None:
            return False
        try:
            if time() - timeout < int(self.nonce[32:], 16):
                return True
        except:
            pass
        return False

def DigestCalcHA1(pszAlg, pszUserName, pszRealm, pszPassword, pszNonce, pszCNonce):
    delim = ':'.encode()
    m = md5()
    m.update(pszUserName.encode())
    m.update(delim)
    m.update(pszRealm.encode())
    m.update(delim)
    m.update(pszPassword.encode())
    HA1 = m.digest()
    if pszAlg == "md5-sess":
        m = md5()
        m.update(HA1)
        m.update(delim)
        m.update(pszNonce.encode())
        m.update(delim)
        m.update(pszCNonce.encode())
        HA1 = m.digest()
    return hexlify(HA1)

def DigestCalcResponse(HA1, pszNonce, pszNonceCount, pszCNonce, pszQop, pszMethod, pszDigestUri, pszHEntity):
    delim = ':'.encode()
    m = md5()
    m.update(pszMethod.encode())
    m.update(delim)
    m.update(pszDigestUri.encode())
    if pszQop == "auth-int":
        m.update(delim)
        m.update(pszHEntity.encode())
    HA2 = m.hexdigest()
    m = md5()
    m.update(HA1)
    m.update(delim)
    m.update(pszNonce.encode())
    m.update(delim)
    if pszNonceCount and pszCNonce and pszQop:
        m.update(pszNonceCount.encode())
        m.update(delim)
        m.update(pszCNonce.encode())
        m.update(delim)
        m.update(pszQop.encode())
        m.update(delim)
    m.update(HA2.encode())
    response = m.hexdigest()
    return response
