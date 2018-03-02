const navIcon = document.getElementById('navigationIcon');

let isNavOpen = false,
    nav = document.getElementById('nav');

navIcon.onclick = () => {
    if (window.innerWidth < 500) {
        mobileToggle();
    } else {
        desktopToggle();
    }
}


$('.nav-link').click(() => {
    $(nav).css('display', 'none');
    isNavOpen = false;
})
;


let desktopToggle = () =>
{
    console.log(isNavOpen, "Status of FLAG");
    if (!isNavOpen) {
        $("html, body").animate({ scrollTop: 0 }, "slow");
        $(nav).slideDown(600);
        isNavOpen = true;
    } else {
        $(nav).slideUp(700);
        isNavOpen = false;
    }
};

let mobileToggle = () =>
{
    let contentWidth;

    if (!isNavOpen) {
        contentWidth = $('.main-container').width();
        $('.main-container').css('width', contentWidth);

        $(".parent-container").animate({
            "marginLeft": ["-90%"]
        }, {
            duration: 700
        });
        isNavOpen = true;

    } else {
        $('.main-container').unbind('touchmove');

        $(".parent-container").animate({
            "marginLeft": ["0%"]
        }, {
            duration: 700,
            complete: function () {
                $('.main-container').css('width', 'auto');
            }
        });
        isNavOpen = false;
    }

};

let hideNav = () => {
    let didScroll;
    let lastScrollTop = 0;
    let delta = 5;
    let navbarHeight = $('#nav').outerHeight();
    $(window).scroll(function (event) {
        didScroll = true;
    });
    setInterval(function () {
        if (didScroll) {
            hasScrolled();
            didScroll = false;
        }
    }, 250);

    function hasScrolled() {
        let st = $(this).scrollTop();
        // Make sure they scroll more than delta
        if (Math.abs(lastScrollTop - st) <= delta)
            return;
        // If they scrolled down and are past the navbar,
        if (st > lastScrollTop && st > navbarHeight) {
            // Scroll Down
            // We want to hide the whole nav
            $(nav).css('display', 'none');
            isNavOpen = false;
        }
        lastScrollTop = st;
    }
};

hideNav();