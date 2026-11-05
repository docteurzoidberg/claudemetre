#!/usr/bin/env python3
"""Sert un dossier sur 127.0.0.1:8931 avec une CSP proche de celle des artefacts claude.ai.

Usage : python3 serve_csp.py <dossier>   Arrêt : fuser -k 8931/tcp
"""
import functools
import http.server
import sys

CSP = ("default-src 'none'; script-src 'nonce-t'; style-src 'unsafe-inline' https://fonts.googleapis.com; "
       "font-src https://fonts.gstatic.com; img-src data: blob:; connect-src 'none'")


class Page(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Content-Security-Policy", CSP)
        super().end_headers()

    def log_message(self, *a):
        pass


http.server.ThreadingHTTPServer(("127.0.0.1", 8931), functools.partial(Page, directory=sys.argv[1])).serve_forever()
