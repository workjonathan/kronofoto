import commonjs from '@rollup/plugin-commonjs';
import resolve from '@rollup/plugin-node-resolve';
import terser from '@rollup/plugin-terser';

const warnHandler = (warning, warn) => {
    // Ignore HTMX eval warning
    if(warning.code == 'EVAL' && warning.id.indexOf('htmx.js') > -1) {
        return;
    }
}

export default [
    {
      input: './kronofoto/static/assets/js/main-dev.js',
      output: {
        file: './kronofoto/static/assets/dist/js/main.js',
        sourcemap: true,
        format: 'iife'
      },
      plugins: [terser(), resolve(), commonjs()],
      onwarn: warnHandler
    },
    {
        input: './kronofoto/static/assets/js/kronofoto-dev.js',
        output: {
            file: './kronofoto/static/assets/js/kronofoto.js',
            sourcemap: true,
            format: 'iife'
        },
        plugins: [terser(), resolve(), commonjs()],
        onwarn: warnHandler
    },
    {
      input: './kronofoto/static/assets/js/exhibit.js',
      output: {
        file: './kronofoto/static/assets/dist/js/exhibit.js',
        sourcemap: true,
        format: 'iife'
      },
      plugins: [terser(), resolve(), commonjs()],
      onwarn: warnHandler
    }
]
