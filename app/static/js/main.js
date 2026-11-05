// دالي دالي — JavaScript أساسي
document.addEventListener("DOMContentLoaded", function () {
    // قائمة الهواتف (الهاتف)
    var toggle = document.querySelector(".menu-toggle");
    var nav = document.querySelector(".nav");
    if (toggle && nav) {
        toggle.addEventListener("click", function () {
            nav.classList.toggle("open");
        });
    }

    // إغلاق القائمة عند النقر على رابط
    var links = document.querySelectorAll(".nav-link");
    links.forEach(function (link) {
        link.addEventListener("click", function () {
            nav.classList.remove("open");
        });
    });
});
