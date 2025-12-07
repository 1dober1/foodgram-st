// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
// Polyfill timers for Node 20+ so @testing-library helpers work.
global.setImmediate =
    global.setImmediate || ((fn, ...args) => setTimeout(fn, 0, ...args));
global.clearImmediate =
    global.clearImmediate || ((id) => clearTimeout(id));

import '@testing-library/jest-dom';
