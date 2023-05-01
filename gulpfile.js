'use strict';
var gulp = require('gulp');
var path = require('path');
var sass = require('gulp-sass')(require('sass'));
const autoprefixer = require('gulp-autoprefixer');
const sourcemaps = require('gulp-sourcemaps');
var config = {
    'root': './kronofoto/static/assets'
};
var concat = require('gulp-concat');
var root = './kronofoto/static/assets';
gulp.task('sass', function () {
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

gulp.task('sass:watch', function () {
    gulp.watch(path.join(config.root, '/scss/**/*.scss'), gulp.series('sass'));
});
