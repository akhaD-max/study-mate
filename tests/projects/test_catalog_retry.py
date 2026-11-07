"""Проверка клиентского повтора без браузера; Node.js необязателен для pytest."""

import shutil
import subprocess
from pathlib import Path

import pytest


def test_catalog_retry_preserves_failed_request():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Для изолированной проверки JavaScript нужен Node.js.")
    script = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const handlers = new Map();
const calls = [];
const banner = {hidden: true};
const button = {disabled: false};
const form = {value: 'original', requestSubmit() { throw Error('Form submitted'); }};
const document = {
    addEventListener(name, fn) {
        if (!handlers.has(name)) handlers.set(name, []);
        handlers.get(name).push(fn);
    },
    getElementById(id) {
        return {'catalog-request-error': banner, 'catalog-filter-form': form}[id];
    },
    querySelector() { return null; },
};
const emit = (name, detail) => {
    for (const fn of handlers.get(name) || []) fn({detail});
};
const click = () => {
    for (const fn of handlers.get('click') || []) {
        fn({target: {closest: () => button}});
    }
};
vm.runInNewContext(fs.readFileSync('static/js/catalog.js', 'utf8'), {
    document,
    htmx: {ajax(method, path, options) {
        calls.push({method, path, options});
        return Promise.resolve();
    }},
});
const request = (path, status, target = 'catalog-content') => ({
    target: {id: target}, xhr: {status}, pathInfo: {finalRequestPath: path},
});
click();
assert.equal(calls.length, 0, 'No retry before a failure');
for (const failure of ['http500', 'htmx:sendError', 'htmx:timeout']) {
    const path = '/projects/?q=Python&direction=science&role=Backend&open_only=false&sort=oldest&page=2';
    const detail = request(path, failure === 'http500' ? 500 : 0);
    emit('htmx:beforeRequest', detail);
    if (failure === 'http500') {
        emit('htmx:beforeSwap', detail);
        assert.equal(detail.shouldSwap, false, '500 preserves the old cards');
    } else {
        emit(failure, detail);
    }
    assert.equal(banner.hidden, false);
    form.value = 'edited filters after failure';
    click();
    const retry = calls.at(-1);
    assert.ok(retry, 'The retry button sends the failed request');
    assert.equal(retry.method, 'GET');
    assert.equal(retry.path, path, 'Retry keeps page and the failed filters');
    assert.equal(retry.options.source, button, 'Retry does not submit the form');
    assert.equal(retry.options.target, '#catalog-content');
    assert.equal(retry.options.swap, 'outerHTML');
    button.disabled = true;
    const count = calls.length;
    click();
    assert.equal(calls.length, count, 'Disabled retry does not send another request');
    button.disabled = false;
    const again = request(path, 0);
    emit('htmx:beforeRequest', again);
    emit('htmx:sendError', again);
    click();
    assert.equal(calls.at(-1).path, path, 'A second failure remains retryable');
    const success = request(path, 200);
    emit('htmx:beforeRequest', success);
    emit('htmx:afterSwap', success);
    assert.equal(banner.hidden, true, 'A successful swap clears the failure');
    const clearedCount = calls.length;
    click();
    assert.equal(calls.length, clearedCount, 'Success clears the retry URL');
}
const invalid = request('/projects/?open_only=invalid', 400);
emit('htmx:beforeRequest', invalid);
emit('htmx:beforeSwap', invalid);
assert.equal(invalid.shouldSwap, true, '400 still displays validation errors');
assert.equal(invalid.isError, false);
emit('htmx:responseError', invalid);
assert.equal(banner.hidden, true);
const old = request('/projects/?q=old', 500);
const current = request('/projects/?q=current', 500);
emit('htmx:beforeRequest', old);
emit('htmx:beforeRequest', current);
emit('htmx:beforeSwap', current);
emit('htmx:sendError', old);
click();
assert.equal(calls.at(-1).path, '/projects/?q=current', 'Old failures cannot overwrite the retry URL');
const unrelated = request('/other/', 500, 'other-content');
emit('htmx:beforeRequest', unrelated);
emit('htmx:beforeSwap', unrelated);
emit('htmx:afterSwap', old);
assert.equal(banner.hidden, false, 'An old swap cannot clear the current failure');
click();
assert.equal(calls.at(-1).path, '/projects/?q=current');
console.log('Catalog retry regression checks passed.');
"""
    result = subprocess.run(
        [node, "-e", script],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
