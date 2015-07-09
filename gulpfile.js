var gulp      = require('gulp'),
    sass      = require('gulp-sass'),
    concat    = require('gulp-concat'),
    minifyCSS = require('gulp-minify-css'),
    rename    = require('gulp-rename'),
    uglify    = require('gulp-uglifyjs');

gulp.task('sass', function () {
  gulp.src('./app/static/sass/*.scss')
    .pipe(sass().on('error', sass.logError))
    .pipe(concat('./app/static/css/style.css'))
    .pipe(minifyCSS())
    .pipe(rename('style.min.css'))
    .pipe(gulp.dest('./app/static/css/'));
});

gulp.task('scripts', function() {
  return gulp.src("./app/static/js/*.js")
    .pipe(concat('./app/static/js/build/phantom-mask.js'))
    .pipe(uglify())
    .pipe(rename('phantom-mask.min.js'))
    .pipe(gulp.dest('./app/static/js/build/'))
});
 
gulp.task('watch', function () {
  gulp.watch('./app/static/js/*.js', ['scripts']);
  gulp.watch('./app/static/sass/**', ['sass']);
});
