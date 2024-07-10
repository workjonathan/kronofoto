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
const exec =  require('child_process').exec;

let HELPERS = {
    execute: (command) => {
        const process = exec(command);
        process.stdout.on('data', (data) => { console.log(data.toString()); })
        process.stderr.on('data', (data) => { console.log(data.toString()); })
        process.on('exit', (code) => {
            console.log('Process exited with code ' + code.toString());
        })
        return process;
    }
}

gulp.task('build:js', () => {
    return HELPERS.execute('rollup -c');
});

var config = {
    'root': './kronofoto/static/assets'
};

gulp.task('build:sass', function () {
    return gulp.src(path.join(config.root, '/scss/index.scss'))
        .pipe(sourcemaps.init())
        .pipe(sass({
            outputStyle: 'compressed',
            includePaths: [
                './node_modules'
            ]
        }).on('error', sass.logError))
        .pipe(autoprefixer())
        .pipe(sourcemaps.write())
        .pipe(gulp.dest(path.join(config.root, './dist/css/')));
});

gulp.task('build:exhibit', function () {
  return gulp.src(path.join(config.root, '/scss/exhibit.scss'))
      .pipe(sourcemaps.init())
      .pipe(sass({
        outputStlye: 'compressed',
        includePaths: [
          './node_modules'
        ]
      }).on('error', sass.logError))
      .pipe(autoprefixer())
      .pipe(sourcemaps.write())
      .pipe(gulp.dest(path.join(config.root, './dist/css/')));
});

gulp.task('watch:all', function () {
    gulp.watch(path.join(config.root, '/scss/**/*.scss'), gulp.series('build:sass'));
    gulp.watch([path.join(config.root, '/scss/exhibit.scss'), path.join(config.root, '/scss/components/exhibit/**/*.scss')], gulp.series('build:exhibit'));
    gulp.watch([path.join(config.root, '/js/**/*.js'), path.join('!' + config.root, '/js/kronofoto.js')], gulp.series('build:js'));
});

gulp.task('build:all', gulp.series('build:sass', 'build:js'));
