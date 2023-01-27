import commonjs from '@rollup/plugin-commonjs';
import resolve from '@rollup/plugin-node-resolve';
import terser from '@rollup/plugin-terser';

export default [
    {
      input: '../static/assets/js/main-dev.js',
      output: {
        file: '../static/assets/js/main.js',
        sourcemap: true,
        format: 'iife'
      },
      plugins: [terser(), resolve(), commonjs()]
    },
    {
      input: '../static/assets/js/kronofoto-dev.js',
      output: {
        file: '../static/assets/js/kronofoto.js',
        sourcemap: true,
        format: 'iife'
      },
      plugins: [terser(), resolve(), commonjs()]
    },
]
