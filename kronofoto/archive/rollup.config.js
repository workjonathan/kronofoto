import commonjs from '@rollup/plugin-commonjs';
import resolve from '@rollup/plugin-node-resolve';

export default [
    {
      input: '../static/assets/js/main-dev.js',
      output: {
        file: '../static/assets/js/main.js',
        format: 'iife'
      },
      plugins: [resolve(), commonjs()]
    },
    {
      input: '../static/assets/js/kronofoto-dev.js',
      output: {
        file: '../static/assets/js/kronofoto.js',
        format: 'iife'
      },
      plugins: [resolve(), commonjs()]
    },
]
