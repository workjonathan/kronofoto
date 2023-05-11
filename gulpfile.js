'use strict';

// Load plugins
const gulp = require('gulp');
const path = require('path');
const commonjs = require('@rollup/plugin-commonjs');
const resolve = require('@rollup/plugin-node-resolve');
const terser = require('@rollup/plugin-terser');
const rollup     = require('rollup');
const sass = require('gulp-sass')(require('sass'));
const autoprefixer = require('gulp-autoprefixer');
const sourcemaps = require('gulp-sourcemaps');
const concat = require('gulp-concat');

// export default [
    // {
//         input: './kronofoto/static/assets/js/main-dev.js',
//         output: {
//             file: './kronofoto/static/assets/js/main.js',
//             sourcemap: true,
//             format: 'iife'
//         },
//         plugins: [terser(), resolve(), commonjs()]
//     },
//     {
//         input: './kronofoto/static/assets/js/kronofoto-dev.js',
//         output: {
//             file: './kronofoto/static/assets/js/kronofoto.js',
//             sourcemap: true,
//             format: 'iife'
//         },
//         plugins: [terser(), resolve(), commonjs()]
//     },
// ]

var config = {
    'root': './kronofoto/static/assets'
};

gulp.task('build:sass', function () {
    return gulp.src(path.join(config.root, '/scss/*.scss'))
        .pipe(sourcemaps.init())
        .pipe(sass({
            outputStlye: 'compressed',
            includePaths: [
                './node_modules/foundation-sites/scss'
            ]
        }).on('error', sass.logError))
        .pipe(autoprefixer())
        .pipe(sourcemaps.write())
        .pipe(gulp.dest(path.join(config.root, './css/')));
});

gulp.task('build:js', function() {
    gulp.src(path.join(config.root, 'js/**/*.js'))
        .pipe(sourcemaps.init())
        .pipe(rollup({
            input: path.join(config.root, 'js/main-dev.js'),
            output: {
                format: 'iife'
            },
            plugins: [terser(), resolve(), commonjs()]
        }))
        .pipe(sourcemaps.write())
        .pipe(gulp.dest(path.join(config.root, 'js/main.js')));

    gulp.src(path.join(config.root, 'js/**/*.js'))
        .pipe(sourcemaps.init())
        .pipe(rollup({
            input: path.join(config.root, 'js/kronofoto-dev.js'),
            output: {
                format: 'iife'
            },
            plugins: [terser(), resolve(), commonjs()]
        }))
        .pipe(sourcemaps.write())
        .pipe(gulp.dest(path.join(config.root, 'js/kronofoto.js')));
});

gulp.task('watch:all', function () {
    gulp.watch(path.join(config.root, '/scss/**/*.scss'), gulp.series('build:sass'));
    gulp.watch(path.join(config.root, '/js/*.js'), gulp.series('build:js'));
});

gulp.task('build:all', function() {
   gulp.series('build:sass', 'build:js')
});
