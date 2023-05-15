import commonjs from '@rollup/plugin-commonjs';
import resolve from '@rollup/plugin-node-resolve';
import terser from '@rollup/plugin-terser';
export default [
    {
      input: './kronofoto/static/assets/js/main-dev.js',
      output: {
        file: './kronofoto/static/assets/dist/js/main.js',
        sourcemap: true,
        format: 'iife'
      },
      plugins: [terser(), resolve(), commonjs()]
    },
    {
      input: './kronofoto/static/assets/js/kronofoto-dev.js',
      output: {
        file: './kronofoto/static/assets/dist/js/kronofoto.js',
        sourcemap: true,
        format: 'iife'
      },
      plugins: [terser(), resolve(), commonjs()]
    },
]
