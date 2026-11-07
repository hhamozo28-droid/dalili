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

    // إظهار/إخفاء رمز الدخول
    var toggleBtn = document.getElementById("togglePass");
    var passInput = document.getElementById("passcode");
    if (toggleBtn && passInput) {
        toggleBtn.addEventListener("click", function () {
            var eye = toggleBtn.querySelector(".icon-eye");
            var eyeOff = toggleBtn.querySelector(".icon-eye-off");
            if (passInput.type === "password") {
                passInput.type = "text";
                eye.style.display = "none";
                eyeOff.style.display = "block";
            } else {
                passInput.type = "password";
                eye.style.display = "block";
                eyeOff.style.display = "none";
            }
        });
    }

    // عرض اسم الملف عند الرفع
    var fileInput = document.getElementById("file-input");
    var fileName = document.getElementById("file-name");
    var submitBtn = document.getElementById("submit-btn");
    if (fileInput) {
        fileInput.addEventListener("change", function () {
            if (fileInput.files.length > 0) {
                var f = fileInput.files[0];
                var sizeKB = Math.round(f.size / 1024);
                fileName.textContent = "✅ " + f.name + " (" + sizeKB + " KB)";
                submitBtn.style.display = "block";
            } else {
                fileName.textContent = "";
                submitBtn.style.display = "none";
            }
        });
    }
});
