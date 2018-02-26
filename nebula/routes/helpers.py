from flask import Flask, session, redirect, url_for, escape, request, render_template, flash, send_from_directory
from nebula import app


def request_wants_json():
    best = request.accept_mimetypes \
        .best_match(['application/json', 'text/html'])
    return best == 'application/json' and \
        request.accept_mimetypes[best] > \
        request.accept_mimetypes['text/html']
