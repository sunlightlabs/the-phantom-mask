var gulp      = require('gulp'),
    sass      = require('gulp-sass'),
    concat    = require('gulp-concat'),
    minifyCSS = require('gulp-minify-css'),
    rename    = require('gulp-rename'),
    uglify    = require('gulp-uglifyjs');
    fs        = require('fs');
    mustache =  require("gulp-mustache");

gulp.task('sass', function () {

    var prefix = '';

    if (process.env.PHANTOM_ENVIRONMENT == 'prod') {
        // this is so dirty - making settings file a yaml or open format next time
        var buf = fs.readFileSync("./config/settings.py", "utf-8");
        var lines = buf.split('\n');
        for (var i = 0; i < lines.length; i++) {
            if (lines[i].indexOf('BASE_PREFIX') != -1) {
                prefix = String(lines[i].split('=')[1].replace(/'/g, '')).trim();
            }
        }
    }

    gulp.src('./app/static/sass/*.scss')
        .pipe(sass().on('error', sass.logError))
        .pipe(concat('./app/static/css/style.css'))
        .pipe(minifyCSS())
        .pipe(rename('style.min.css'))
        .pipe(mustache({
            URL_PREFIX: prefix
        }))
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
