# Copyright (C) 2016 Denis Gasparin <denis@gasparin.net>
#
# This file is part of Pgrepup.
#
# Pgrepup is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pgrepup is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Pgrepup. If not, see <http://www.gnu.org/licenses/>.
import base64
import getpass
import os
import sys
try:  # Python 2
    from ConfigParser import NoOptionError
except ImportError:  # Python 3
    from configparser import NoOptionError
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import InvalidToken
from ..config import config


this = sys.modules[__name__]
this.key = None


def encrypt(string_to_encrypt):
    encrypted_passwords = config().get('Security', 'encrypted_credentials') == 'y'
    if not encrypted_passwords:
        return string_to_encrypt

    f = Fernet(_get_key())
    return f.encrypt(string_to_encrypt)


def decrypt(password):
    encrypted_passwords = config().get('Security', 'encrypted_credentials') == 'y'
    if not encrypted_passwords:
        return password

    try:
        f = Fernet(_get_key())
        return f.decrypt(password)
    except InvalidToken:
        print("Invalid master password")
        sys.exit(-1)


def _get_key():
    if this.key:
        return this.key

    secret = getpass.getpass()
    try:
        salt = config().get('Security', 'salt')
    except NoOptionError:
        salt = base64.urlsafe_b64encode(os.urandom(16))
        config().set('Security', 'salt', salt)

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    this.key = base64.urlsafe_b64encode(kdf.derive(secret))
    return this.key
