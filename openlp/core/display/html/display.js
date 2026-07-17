/**
 * display.js is the main Javascript file that is used to drive the display.
 */


/**
 * Background type enumeration
 */
var BackgroundType = {
  Transparent: "transparent",
  Solid: "solid",
  Gradient: "gradient",
  Video: "video",
  Image: "image"
};

/**
 * Gradient type enumeration
 */
var GradientType = {
  Horizontal: "horizontal",
  LeftTop: "leftTop",
  LeftBottom: "leftBottom",
  Vertical: "vertical",
  Circular: "circular"
};

/**
 * Horizontal alignment enumeration
 */
var HorizontalAlign = {
  Left: 0,
  Right: 1,
  Center: 2,
  Justify: 3
};

/**
 * Vertical alignment enumeration
 */
var VerticalAlign = {
  Top: 0,
  Middle: 1,
  Bottom: 2
};

/**
 * Transition type enumeration
 */
var TransitionType = {
  Fade: 0,
  Slide: 1,
  Convex: 2,
  Concave: 3,
  Zoom: 4
};

/**
 * Transition speed enumeration
 */
var TransitionSpeed = {
  Normal: 0,
  Fast: 1,
  Slow: 2
};


/**
 * Transition direction enumeration
 */
var TransitionDirection = {
  Horizontal: 0,
  Vertical: 1
};

/**
 * Audio state enumeration
 */
var AudioState = {
  Playing: "playing",
  Paused: "paused",
  Stopped: "stopped"
};

/**
 * Transition state enumeration
 */
var TransitionState = {
  EntranceTransition: "entranceTransition",
  NoTransition: "noTransition",
  ExitTransition: "exitTransition"
};

/**
 * Animation state enumeration
 */
var AnimationState = {
  NoAnimation: "noAnimation",
  ScrollingText: "scrollingText",
  NonScrollingText: "noScrollingText"
};

/**
 * Alert location enumeration
 */
var AlertLocation = {
  Top: 0,
  Middle: 1,
  Bottom: 2
};

/**
 * Alert state enumeration
 */
var AlertState = {
  Displaying: "displaying",
  NotDisplaying: "notDisplaying"
};

/**
 * Alert delay enumeration
 */
var AlertDelay = {
  FiftyMilliseconds: 50,
  OneSecond: 1000,
  OnePointFiveSeconds: 1500
};

/**
 * Map of horizontal aligns to their CSS names for the text-align property
 */
var HorizontalAlignCSS = {
  [HorizontalAlign.Justify]: "justify",
  [HorizontalAlign.Center]: "center",
  [HorizontalAlign.Left]: "left",
  [HorizontalAlign.Right]: "right",
};

/**
 * Map of vertical aligns to their CSS names for the justify-content property
 */
var VerticalAlignCSS = {
  [VerticalAlign.Top]: "flex-start",
  [VerticalAlign.Middle]: "center",
  [VerticalAlign.Bottom]: "flex-end"
};

/**
 * Return an array of elements based on the selector query
 * @param {string} selector - The selector to find elements
 * @returns {array} An array of matching elements
 */
function $(selector) {
  return Array.from(document.querySelectorAll(selector));
}

/**
 * Build linear gradient CSS
 * @private
 * @param {string} direction - The direction or angle of the gradient e.g. to bottom or 90deg
 * @param {string} startColor - The starting color
 * @param {string} endColor - The ending color
 * @returns {string} A string of the gradient CSS
 */
function _buildLinearGradient(direction, startColor, endColor) {
  return "linear-gradient(" + direction + ", " + startColor + ", " + endColor + ") fixed";
}

/**
 * Build radial gradient CSS
 * @private
 * @param {string} width - Width of the gradient
 * @param {string} startColor - The starting color
 * @param {string} endColor - The ending color
 * @returns {string} A string of the gradient CSS
 */
function _buildRadialGradient(width, startColor, endColor) {
  return "radial-gradient(" + startColor + ", " + endColor + ") fixed";
}

/**
 * Build a set of text shadows to form an outline
 * @private
 * @param {number} size - The desired width of the outline
 * @param {string} color - The color of the outline
 * @returns {Array} A list of shadows to be given to "text-shadow"
 */
function _buildTextOutline(size, color) {
  let shadows = [];
  // Outlines work from -(size) to +(size)
  let from = size * -1;
  // Loop through all the possible size iterations and add them to the array
  for (let i = from; i <= size; i++) {
    for (let j = from; j <= size; j++) {
      shadows.push(color + " " + i + "pt " + j + "pt 0pt");
    }
  }
  return shadows;
}

/**
 * Build a text shadow
 * @private
 * @param {number} offset - The offset of the shadow
 * @param {number} size - The desired width of the shadow
 * @param {string} color - The color that the shadow should be
 * @returns {Array} A list of shadows to be given to "text-shadow"
 */
function _buildTextShadow(offset, size, color) {
  let shadows = [];
  let from = (size * -1) + offset;
  let to = size + offset;
  for (let i = from; i <= to; i++) {
    for (let j = from; j <= to; j++) {
      shadows.push(color + " " + i + "pt " + j + "pt 0pt");
    }
  }
  return shadows;
}


/**
 * Get a style value from an element (computed or manual)
 * @private
 * @param {Object} element - The element whose style we want
 * @param {string} style - The name of the style we want
 * @returns {(Number|string)} The style value (type depends on the style)
 */
function _getStyle(element, style) {
  return document.defaultView.getComputedStyle(element).getPropertyValue(style);
}

/**
 * Convert newlines to <br> tags
 * @private
 * @param {string} text - The text to parse
 * @returns {string} The text now with <br> tags
 */
function _nl2br(text) {
  return text.replace(/\r\n/g, "\n").replace(/\n/g, "<br>");
}

/**
 * Prepare text by creating paragraphs and calling _nl2br to convert newlines to <br> tags
 * @private
 * @param {string} text - The text to parse
 * @returns {string} The text now with <p> and <br> tags
 */
function _prepareText(text) {
  return "<p>" + _nl2br(text) + "</p>";
}

/**
 * Change a camelCaseString to a camel-case-string
 * @private
 * @param {string} text
 * @returns {string} the Un-camel-case-ified string
 */
function _fromCamelCase(text) {
  return text.replace(/([A-Z])/g, function (match, submatch) {
    return '-' + submatch.toLowerCase();
  });
}

/**
 * Create a CSS style
 * @private
 * @param {string} selector - The selector for this style
 * @param {Object} rules - The rules to apply to the style
 * @param {string} [styleId] - Explicit id for the <style> element, needed when the
 *                             selector contains characters that make a bad element id
 */
function _createStyle(selector, rules, styleId) {
  var style;
  var id = styleId || selector.replace("#", "").replace(" .", "-").replace(".", "-").replace(" ", "_");
  if ($("style#" + id).length != 0) {
    style = $("style#" + id)[0];
  }
  else {
    style = document.createElement("style");
    document.getElementsByTagName("head")[0].appendChild(style);
    style.type = "text/css";
    style.id = id;
  }
  var rulesString = selector + " { ";
  for (var key in rules) {
    var ruleValue = rules[key];
    var ruleKey = _fromCamelCase(key);
    rulesString += "" + ruleKey + ": " + ruleValue + ";";
  }
  rulesString += " } ";
  if (style.styleSheet) {
    style.styleSheet.cssText = rulesString;
  }
  else {
    // Replace any previous rules, otherwise the style element grows on every update
    style.textContent = rulesString;
  }
}

/**
 * Fixes font name to match CSS names.
 * @param {string} fontName Font Name
 * @returns Fixed Font Name
 */
function _fixFontName(fontName) {
  if (!fontName || (fontName == 'Sans Serif')) {
    return 'sans-serif';
  }

  return "'" + fontName + "'";
}

/**
 * The Display object is what we use from OpenLP
 */
var Display = {
  /** @type {HTMLElement} */
  _slidesContainer: null,
  /** @type {HTMLElement} */
  _footerContainer: null,
  /** @type {HTMLElement} */
  _backgroundsContainer: null,
  _alerts: [],
  _slides: {},
  _alertSettings: {},
  _alertState: AlertState.NotDisplaying,
  _transitionState: TransitionState.NoTransition,
  _animationState: AnimationState.NoAnimation,
  _doTransitions: false,
  _doItemTransitions: false,
  _skipNextTransition: false,
  _themeApplied: true,
  _revealConfig: {
    margin: 0.0,
    minScale: 1.0,
    maxScale: 1.0,
    controls: false,
    progress: false,
    history: false,
    keyboard: false,
    overview: false,
    center: false,
    touch: false,
    help: false,
    transition: "none",
    backgroundTransition: "none",
    viewDistance: 9999,
    width: "100%",
    height: "100%"
  },
  _lastRequestAnimationFrameHandle: null,

  /**
   * Start up reveal and do any other initialisation
   * @param {object} options - The initialisation options:
   *                           * {bool} isDisplay         - Is this a real display output
   *                           * {bool} doItemTransitions - Transition between service items
   *                           * {bool} hideMouse         - Hide the cursor when hovering on this display
   */
  init: function (options) {
    // Set defaults for undefined values
    options = options || {};
    let isDisplay = options.isDisplay || false;
    let doItemTransitions = options.doItemTransitions || false;
    let hideMouse = options.hideMouse || false;
    if (options.slideNumbersInFooter) {
      Display._revealConfig.slideNumber = Display.setFooterSlideNumbers;
    }

    // Now continue to initialisation
    if (!isDisplay) {
      document.body.classList.add('checkerboard');
    }
    if (hideMouse) {
      document.body.classList.add('hide-mouse');
    }
    Display._slidesContainer = $(".slides")[0];
    Display._footerContainer = $(".footer")[0];
    Display._backgroundsContainer = $(".backgrounds")[0];
    Display._doTransitions = isDisplay;
    Reveal.initialize(Display._revealConfig);
    Reveal.addEventListener('slidechanged', Display._onSlideChanged);
    Display.setItemTransition(doItemTransitions && isDisplay);
    displayWatcher.setInitialised(true);
  },
  /**
   * Reinitialise Reveal
   */
  reinit: function () {
    Reveal.sync();
    // Python expects to be on first page after reinit
    Reveal.slide(0);
  },
  /**
   * Enable/Disable item transitions
   */
  setItemTransition: function (enable) {
    Display._doItemTransitions = enable;
    var body = $("body")[0];
    if (enable) {
      body.classList.add("transition");
      Reveal.configure({"backgroundTransition": "fade", "transitionSpeed": "default"});
    } else {
      body.classList.remove("transition");
      Reveal.configure({"backgroundTransition": "none"});
    }
  },
  /**
   * Clear the current list of slides
  */
  clearSlides: function () {
    Display._slidesContainer.innerHTML = "";
    Display._clearSlidesList();
  },
  /**
   * Clear the current list of slides
  */
  _clearSlidesList: function () {
    Display._footerContainer.innerHTML = "";
    Display._slides = {};
  },
  /**
   * Add new item/slides, replacing the old one
   * Clears current list of slides but allows time for a transition animation
   * Items are ordered newest to oldest in the slides container
   * @param {element} new_slides - New slides to display
   * @param {element} is_text - Used to decide if the theme main area constraints should apply
  */
  replaceSlides: function (new_slides, is_text=false) {
    if (Display._doItemTransitions) {
      new_slides.setAttribute('data-transition', "fade");
      new_slides.setAttribute('data-transition-speed', "default");
    }
    new_slides.classList.add("future");
    Display.applyTheme(new_slides, is_text);
    Display._slidesContainer.prepend(new_slides);
    var currentSlide = Reveal.getIndices();
    if (Display._doItemTransitions && Display._slidesContainer.children.length >= 2 && !Display._skipNextTransition) {
      // Set the slide one section ahead so we'll stay on the old slide after reinit
      Reveal.slide(1, currentSlide.v);
      Display.reinit();
      // Timeout to allow time to transition before deleting the old slides
      setTimeout (Display._removeLastSection, 5000);
    } else {
      Reveal.slide(0, currentSlide.v);
      Reveal.sync();
      Display._removeLastSection();
      Display._skipNextTransition = false;
    }
  },
  /**
   * Removes the last slides item if there are more than one
  */
  _removeLastSection: function () {
    if (Display._slidesContainer.children.length > 1) {
      Display._slidesContainer.lastChild.remove();
    }
  },
  /**
   * Checks if the present slide content fits within the slide
  */
  doesContentFit: function () {
    var textSlides = $("section.text-slides");
    if (textSlides.length === 0) {
      var footer = Display._footerContainer;
      return footer.clientHeight >= footer.scrollHeight;
    }
    var container = textSlides[0];
    // The slide sections are absolutely positioned within the main area container,
    // so the container's own scrollHeight misses content which overflows upwards
    // (middle/bottom vertical alignment). Measure the content of each slide
    // directly instead and compare it against the space the theme allows.
    var contentHeight = 0;
    for (var i = 0; i < container.children.length; i++) {
      contentHeight = Math.max(contentHeight, container.children[i].scrollHeight);
    }
    var containerStyle = window.getComputedStyle(container);
    var availableHeight = container.clientHeight - (parseFloat(containerStyle.paddingTop) || 0) -
                          (parseFloat(containerStyle.paddingBottom) || 0);
    return availableHeight >= contentHeight;
  },
  /**
   * Generate the OpenLP startup splashscreen
   * @param {string} bg_color - The background color
   * @param {string} image - Path to the splash image
   */
  setStartupSplashScreen: function(bg_color, image) {
    Display._clearSlidesList();
    var section = document.createElement("section");
    section.setAttribute("id", 0);
    section.setAttribute("data-background", bg_color);
    section.setAttribute("style", "height: 100%; width: 100%;");
    var img = document.createElement('img');
    img.src = Display._getFileUrl(image);
    img.setAttribute("style", "position: absolute; top: 0; bottom: 0; left: 0; right: 0; margin: auto; max-height: 100%; max-width: 100%");
    section.appendChild(img);
    Display._slides['0'] = 0;
    Display.replaceSlides(section);
  },
  /**
   * Set fullscreen image from path
   * @param {string} bg_color - The background color
   * @param {string} image - Path to the image
   */
  setFullscreenImage: function(bg_color, image) {
    Display.clearSlides();
    var section = document.createElement("section");
    section.setAttribute("id", 0);
    section.setAttribute("data-background", bg_color);
    section.setAttribute("style", "height: 100%; width: 100%;");
    var img = document.createElement('img');
    img.src = image;
    img.setAttribute("style", "height: 100%; width: 100%; margin: 0; object-fit: contain;");
    section.appendChild(img);
    Display._slides['0'] = 0;
    Display.replaceSlides(section);
  },
  /**
   * Set fullscreen image from base64 data
   * @param {string} bg_color - The background color
   * @param {string} image_data - base64 encoded image data
   */
  setFullscreenImageFromData: function(bg_color, image_data) {
    Display.clearSlides();
    var section = document.createElement("section");
    section.setAttribute("id", 0);
    section.setAttribute("data-background", bg_color);
    section.setAttribute("style", "height: 100%; width: 100%;");
    var img = document.createElement('img');
    img.src = 'data:image/jpeg;base64,' + image_data;
    img.setAttribute("style", "height: 100%; width: 100%");
    section.appendChild(img);
    Display._slidesContainer.appendChild(section);
    Display._slides['0'] = 0;
    Display.reinit();
  },
  /**
   * Display an alert. If there's an alert already showing, add this one to the queue
   * @param {string} text - The alert text
   * @param {Object} JSON object - The settings for the alert object
  */
  alert: function (text, settings) {
    if (text == "") {
      return null;
    }
    if (Display._alertState === AlertState.Displaying) {
      Display.addAlertToQueue(text, settings);
    }
    else {
      Display.showAlert(text, settings);
    }
  },
  /**
   * Show the alert on the screen
   * @param {string} text - The alert text
   * @param {Object} JSON object - The settings for the alert
  */
  showAlert: function (text, settings) {
    var alertBackground = $('#alert-background')[0];
    var alertText = $('#alert-text')[0];
    // create styles for the alerts from the settings
    _createStyle("#alert-background.settings", {
      backgroundColor: settings.backgroundColor,
      fontFamily: _fixFontName(settings.fontFace),
      fontSize: settings.fontSize.toString() + "pt",
      color: settings.fontColor
    });
    alertBackground.classList.add("settings");
    alertBackground.classList.replace("hide", "show");
    alertText.innerHTML = text;
    Display.setAlertLocation(settings.location);
    Display._transitionState = TransitionState.EntranceTransition;
    /* Check if the alert is a queued alert */
    if (Display._alertState !== AlertState.Displaying) {
      Display._alertState = AlertState.Displaying;
    }
    alertBackground.addEventListener('transitionend', Display.alertTransitionEndEvent, false);
    alertText.addEventListener('animationend', Display.alertAnimationEndEvent, false);
    /* Either scroll the alert, or make it disappear at the end of its time */
    if (settings.scroll) {
      Display._animationState = AnimationState.ScrollingText;
      alertText.classList.add('scrolling');
      alertText.classList.replace("hide", "show");
      var animationSettings = "alert-scrolling-text " + settings.timeout +
                              "s linear 0.6s " + settings.repeat + " normal";
      alertText.style.animation = animationSettings;
    }
    else {
      Display._animationState = AnimationState.NonScrollingText;
      alertText.classList.replace("hide", "show");
      setTimeout (function () {
        Display._animationState = AnimationState.NoAnimation;
        Display.hideAlert();
      }, settings.timeout * AlertDelay.OneSecond);
    }
  },
  /**
   * Hide the alert at the end
   */
  hideAlert: function () {
    var alertBackground = $('#alert-background')[0];
    var alertText = $('#alert-text')[0];
    Display._transitionState = TransitionState.ExitTransition;
    alertText.classList.replace("show", "hide");
    alertBackground.classList.replace("show", "hide");
    alertText.style.animation = "";
    Display._alertState = AlertState.NotDisplaying;
  },
  /**
   * Add an alert to the alert queue
   * @param {string} text - The alert text to be displayed
   * @param {Object} setttings - JSON object containing the settings for the alert
   */
  addAlertToQueue: function (text, settings) {
    Display._alerts.push({text: text, settings: settings});
  },
  /**
   * The alertTransitionEndEvent called after a transition has ended
   */
  alertTransitionEndEvent: function (e) {
    e.stopPropagation();
    if (Display._transitionState === TransitionState.EntranceTransition) {
      Display._transitionState = TransitionState.NoTransition;
    }
    else if (Display._transitionState === TransitionState.ExitTransition) {
      Display._transitionState = TransitionState.NoTransition;
      Display.hideAlert();
      Display.showNextAlert();
    }
  },
  /**
   * The alertAnimationEndEvent called after an animation has ended
   */
  alertAnimationEndEvent: function (e) {
    e.stopPropagation();
    Display.hideAlert();
  },
  /**
   * Set the location of the alert
   * @param {int} location - Integer number with the location of the alert on screen
   */
  setAlertLocation: function (location) {
    var alertContainer = $(".alert-container")[0];
    // Remove an existing location classes
    alertContainer.classList.remove("top");
    alertContainer.classList.remove("middle");
    alertContainer.classList.remove("bottom");
    // Apply the location class we want
    switch (location) {
      case AlertLocation.Top:
        alertContainer.classList.add("top");
        break;
      case AlertLocation.Middle:
        alertContainer.classList.add("middle");
        break;
      case AlertLocation.Bottom:
      default:
        alertContainer.classList.add("bottom");
        break;
    }
  },
  /**
  * Display the next alert in the queue
  */
  showNextAlert: function () {
    if (Display._alerts.length > 0) {
      var alertObject = Display._alerts.shift();
      Display._alertState = AlertState.DisplayingFromQueue;
      Display.showAlert(alertObject.text, alertObject.settings);
    }
    else {
      // For the tests
      return null;
    }
  },
  /**
   * Create a text slide.
   * @param {string} verse - The verse number, e.g. "v1"
   * @param {string} text - The HTML for the verse, e.g. "line1<br>line2"
   */
  _createTextSlide: function (verse, text) {
    var slide;
    var html = _prepareText(text);
    slide = document.createElement("section");
    slide.setAttribute("id", verse);
    // The "future" class is used internally by reveal, it's used here to hide newly added slides
    slide.classList.add("future");
    slide.innerHTML = html;
    return slide;
  },

  _onSlideChanged: function(event) {
    Display._footerContainer.querySelectorAll('.footer-item')
      .forEach(footerItem => footerItem.classList.remove('active'));
    var currentSlideNth = parseInt(event.currentSlide.getAttribute('data-slide'));
    var newActiveFooter = Display._footerContainer.querySelector('.footer-item[data-slide="' + currentSlideNth + '"]');

    if (newActiveFooter) {
      newActiveFooter.classList.add('active');
    }
  },

  /**
   * Set text slides.
   * @param {Object[]} slides - A list of slides to add as JS objects: {"verse": "v1", "text": "line 1\nline2"}
   */
  setTextSlides: function (slides) {
    Display._clearSlidesList();
    var slide_html;
    var parentSection = document.createElement("section");
    parentSection.classList = "text-slides";
    slides.forEach(function (slide, index) {
      slide_html = Display._createTextSlide(slide.verse, slide.text);
      slide_html.setAttribute('data-slide', index);
      parentSection.appendChild(slide_html);
      Display._slides[slide.verse] = parentSection.children.length - 1;
      if (slide.footer) {
        var footerSlide = document.createElement('div');
        footerSlide.classList.add('footer-item');
        footerSlide.setAttribute('data-slide', index);
        var currentSlide = Reveal.getIndices();
        if (currentSlide) {
          currentSlide = currentSlide.v;
        } else {
          currentSlide = 0;
        }
        if (index == currentSlide) {
          footerSlide.classList.add('active');
        }
        footerSlide.innerHTML = slide.footer;
        Display._footerContainer.append(footerSlide);
      }
    });
    Display.replaceSlides(parentSection, true);
  },
  /**
   * Set a single text slide. This changes the slide with no transition.
   * Prevents the need to reapply the theme if only changing content.
   * @param String slide - Text to put on the slide
   */
  setTextSlide: function (text) {
    if (Display._slides.hasOwnProperty("test-slide") && Object.keys(Display._slides).length === 1) {
      var slide = $("#" + "test-slide")[0];
      var html = _prepareText(text);
      if (slide.innerHTML != html) {
        slide.innerHTML = html;
      }
      if (!Display._themeApplied) {
        Display.applyTheme(slide.parentElement);
      }
    } else {
      Display._clearSlidesList();
      var slide_html;
      var parentSection = document.createElement("section");
      parentSection.classList = "text-slides";
      slide_html = Display._createTextSlide("test-slide", text);
      slide_html.setAttribute('data-slide', 0);
      parentSection.appendChild(slide_html);
      Display._slides["test-slide"] = 0;
      Display.applyTheme(parentSection);
      Display._slidesContainer.innerHTML = "";
      Display._slidesContainer.prepend(parentSection);
      Display.reinit();
    }
  },
  /**
   * Set the test slide text and report whether it fits within the main area, in a
   * single call. Pagination measures many candidate texts in a row, so combining
   * both operations halves the number of synchronous round trips from Python.
   * @param String text - Text to measure
   * @returns {boolean} true when the text fits on the slide
   */
  setTextSlideAndCheckFit: function (text) {
    Display.setTextSlide(text);
    return Display.doesContentFit();
  },
  /**
   * Set image slides
   * @param {Object[]} slides - A list of images to add as JS objects [{"path": "url/to/file"}]
   */
  setImageSlides: function (slides) {
    Display._clearSlidesList();
    var parentSection = document.createElement("section");
    slides.forEach(function (slide, index) {
      var section = document.createElement("section");
      section.setAttribute("id", index);
      section.setAttribute("style", "height: 100%; width: 100%;");
      var img = document.createElement('img');
      img.src = Display._getFileUrl(slide.path);
      img.setAttribute("style", "width: 100%; height: 100%; margin: 0; object-fit: contain;");
      img.setAttribute('data-slide', index);
      section.appendChild(img);
      parentSection.appendChild(section);
      Display._slides[index.toString()] = index;
    });
    Display.replaceSlides(parentSection);
  },
  /**
   * Set a video
   * @param {Object} video - The video to show as a JS object: {"path": "url/to/file"}
   */
  setVideo: function (video) {
    Display._clearSlidesList();
    var section = document.createElement("section");
    section.setAttribute("data-background", "#000");
    var videoElement = document.createElement("video");
    videoElement.src = video.path;
    videoElement.preload = "auto";
    videoElement.setAttribute("id", "video");
    videoElement.setAttribute("style", "height: 100%; width: 100%;");
    videoElement.setAttribute('data-slide', 0);
    videoElement.autoplay = false;
    // All the update methods below are Python functions, hence not camelCase
    videoElement.addEventListener("durationchange", function (event) {
      mediaWatcher.update_duration(event.target.duration);
    });
    videoElement.addEventListener("timeupdate", function (event) {
      mediaWatcher.update_progress(event.target.currentTime);
    });
    videoElement.addEventListener("volumeupdate", function (event) {
      mediaWatcher.update_volume(event.target.volume);
    });
    videoElement.addEventListener("ratechange", function (event) {
      mediaWatcher.update_playback_rate(event.target.playbackRate);
    });
    videoElement.addEventListener("ended", function (event) {
      mediaWatcher.has_ended(event.target.ended);
    });
    videoElement.addEventListener("muted", function (event) {
      mediaWatcher.has_muted(event.target.muted);
    });
    section.appendChild(videoElement);
    Display.replaceSlides(section);
  },
  /**
   * Play a video
   */
  playVideo: function () {
    var videoElem = $("#video");
    if (videoElem.length == 1) {
      videoElem[0].play();
    }
  },
  /**
   * Pause a video
   */
  pauseVideo: function () {
    var videoElem = $("#video");
    if (videoElem.length == 1) {
      videoElem[0].pause();
    }
  },
  /**
   * Stop a video
   */
  stopVideo: function () {
    var videoElem = $("#video");
    if (videoElem.length == 1) {
      videoElem[0].pause();
      videoElem[0].currentTime = 0.0;
    }
  },
  /**
   * Go to a particular time in a video
   * @param seconds The position in seconds to seek to
   */
  seekVideo: function (seconds) {
    var videoElem = $("#video");
    if (videoElem.length == 1) {
      videoElem[0].currentTime = seconds;
    }
  },
  /**
   * Set the playback rate of a video
   * @param rate A Double of the rate. 1.0 => 100% speed, 0.75 => 75% speed, 1.25 => 125% speed, etc.
   */
  setPlaybackRate: function (rate) {
    var videoElem = $("#video");
    if (videoElem.length == 1) {
      videoElem[0].playbackRate = rate;
    }
  },
  /**
   * Set the volume
   * @param level The volume level from 0 to 100.
   */
  setVideoVolume: function (level) {
    var videoElem = $("#video");
    if (videoElem.length == 1) {
      videoElem[0].volume = level / 100.0;
    }
  },
  /**
   * Mute the volume
   */
  toggleVideoMute: function () {
    var videoElem = $("#video");
    if (videoElem.length == 1) {
      videoElem[0].muted = !videoElem[0].muted;
    }
  },
  /**
   * Clear the background audio playlist
   */
  clearPlaylist: function () {
    var backgroundAudoElem = $("#background-audio");
    if (backgroundAudoElem.length == 1) {
      var audio = backgroundAudoElem[0];
      /* audio.playList */
    }
  },
  /**
   * Add background audio
   * @param files The list of files as objects in an array
   */
  addBackgroundAudio: function (files) {
  },
  /**
   * Go to a slide.
   * @param slide The slide number or name, e.g. "v1", 0
   */
  goToSlide: function (slide) {
    if (Display._slides.hasOwnProperty(slide)) {
      Reveal.slide(0, Display._slides[slide]);
    }
    else {
      Reveal.slide(0, slide);
    }
  },
  /**
   * Go to the next slide in the list
  */
  next: Reveal.nextFragment,
  /**
   * Go to the previous slide in the list
  */
  prev: Reveal.prevFragment,
  /**
   * Blank the screen
  */
  toBlack: function () {
    Display._logTransition("toBlack");
    return new Promise((resolve, reject) => {
      /* Avoid race conditions where display goes to transparent and quickly goes to black */
      Display._abortLastTransitionOperation();
      /*
        Reveal's black overlay should be shown before the transitions are
        restored, to avoid screen flashes
      */
      Display._restorePauseBehavior();
      Display._requestAnimationFrameExclusive(function() {
        if (!Reveal.isPaused()) {
          Reveal.togglePause();
        }
        Display._reenableGlobalTransitions(function() {
          var documentBody = $("body")[0];
          documentBody.style.opacity = 1;
          resolve();
        });
      });
    });
  },
  /**
   * Hide all but theme background
  */
  toTheme: function () {
    Display._logTransition("toTheme");
    return new Promise((resolve, reject) => {
      Display._abortLastTransitionOperation();
      /*
        Reveal's black overlay should be shown before the transitions are
        restored, to avoid screen flashes
      */
      Display._restorePauseBehavior();
      var documentBody = $("body")[0];
      documentBody.style.opacity = 1;
      Display._slidesContainer.style.opacity = 0;
      Display._footerContainer.style.opacity = 0;
      if (Reveal.isPaused()) {
        Reveal.togglePause();
      }
      Display._reenableGlobalTransitions(function() {
        resolve();
      });
    });
  },
  /**
   * Hide everything (CAUTION: Causes a invisible mouse barrier)
  */
  toTransparent: function () {
    Display._logTransition("toTransparent");
    return new Promise((resolve, reject) => {
      Display._abortLastTransitionOperation();
      var documentBody = $("body")[0];
      /*
        The body opacity transition below is what eventually resolves this promise. A CSS
        transition only runs when the value actually changes, so capture whether the body
        is already fully transparent BEFORE setting the style: in that case no
        'transitionend' will ever fire and waiting for one would leave this promise (and
        Python, which hides the window when it resolves) hanging forever. This happens
        when Show Desktop is requested twice, or when a previous show()'s animation frame
        was cancelled before it could restore the opacity.
      */
      var alreadyTransparent = window.getComputedStyle(documentBody).opacity === "0";
      documentBody.style.opacity = 0;
      if (!Reveal.isPaused()) {
        /*
          Removing previously the overlay if it's not paused, to avoid a
          content flash while going from black screen to transparent
        */
        document.body.classList.add('is-desktop');
        Reveal.togglePause();
      }
      function finishTransparent() {
        /*
          Disabling all transitions (except body) to allow the Webview to attain the
          transparent state before it gets hidden by Qt.
        */
        document.body.classList.add('disable-transitions');
        document.body.classList.add('is-desktop');
        Display._slidesContainer.style.opacity = 0;
        Display._footerContainer.style.opacity = 0;
        /*
          Repainting before hiding the Webview to avoid flashes when
          showing it again.
        */
        displayWatcher.pleaseRepaint();
        /* Waiting for repaint to happen before saying that it's done. */
        Display._requestAnimationFrameExclusive(function() {
          /* We're transparent now, aborting any transition event between */
          Display._abortLastTransitionOperation();
          console.debug("[transition] toTransparent complete");
          resolve();
        });
      }
      if (alreadyTransparent) {
        console.debug("[transition] toTransparent: body already transparent, completing immediately");
        finishTransparent();
        return;
      }
      /*
        Waiting for body transition to happen, now it would be safe to
        hide the Webview (as other transitions were suppressed)
      */
      Display._abortLastTransitionOperation();
      Display._addTransitionEndEventToBody(transitionEndEvent);
      function transitionEndEvent(e) {
        // Targeting only body
        if (e.target != documentBody) {
          return;
        }
        finishTransparent();
      }
    });
  },
  /**
   * Show the screen
  */
  show: function () {
    Display._logTransition("show");
    return new Promise((resolve, reject) => {
      var documentBody = $("body")[0];
      /*
        Removing transitionend event, avoids the content being hidden if the user
        tries to show content again before toTransparent() transitionend event
        happens
      */
      Display._abortLastTransitionOperation();

      Display._slidesContainer.style.opacity = 1;
      Display._footerContainer.style.opacity = 1;
      if (Reveal.isPaused()) {
        Reveal.togglePause();
      }
      Display._restorePauseBehavior();
      Display._reenableGlobalTransitions(function() {
        documentBody.style.opacity = 1;
        resolve();
      });
    });
  },

  /**
   * Log a display state transition with the state it starts from, so that stuck or
   * out-of-order mode switches can be diagnosed from the OpenLP log (JS console
   * messages are forwarded to the Python logger).
   * @param {string} name - The transition being started
   */
  _logTransition: function(name) {
    var documentBody = $("body")[0];
    console.debug("[transition] " + name + " requested: paused=" + Reveal.isPaused() +
                  ", bodyOpacity=" + window.getComputedStyle(documentBody).opacity +
                  ", bodyClasses=\"" + documentBody.className + "\"");
  },

  _reenableGlobalTransitions: function(afterCallback) {
    Display._requestAnimationFrameExclusive(function() {
      /*
        Waiting for the previous opacity + unpause operations to complete
        to restore the transitions behavior
      */
      document.body.classList.remove('disable-transitions');
      if (typeof afterCallback === 'function') {
        afterCallback();
      }
    });
  },

  /**
   * Shows again the Reveal's black pause overlay that was
   * hidden before Webview was hidden
   */
  _restorePauseBehavior: function() {
    document.body.classList.remove('is-desktop');
  },

  /**
   * Cancels previous requested animationFrame.
   * Last animationFrame should be aborted to avoid race condition bugs when
   * the user changes the view modes too quickly, for example.
   */
  _requestAnimationFrameExclusive: function(callback) {
    cancelAnimationFrame(Display._lastRequestAnimationFrameHandle);
    Display._lastRequestAnimationFrameHandle = requestAnimationFrame(callback);
  },

  /**
   * Aborts last body's transitionend and requestAnimationFrame's events, to avoid
   * race condition bugs.
   */
  _abortLastTransitionOperation: function() {
    Display._removeTransitionEndEventToBody();
    cancelAnimationFrame(Display._lastRequestAnimationFrameHandle);
  },

  /**
   * Intercepts the addEventListener call and stores it, so that it acts
   * like the ontransitionend GlobalEventHandler.
   */
  _addTransitionEndEventToBody: function(listener) {
    Display._lastTransitionEndBodyEvent = listener;
    document.body.addEventListener('transitionend', listener);
  },

  _removeTransitionEndEventToBody: function() {
    document.body.removeEventListener('transitionend', Display._lastTransitionEndBodyEvent);
  },

  /**
   * Figure out how many lines can fit on a slide given the font size
   * @param fontSize The font size in pts
   */
  calculateLineCount: function (fontSize) {
    var p = $(".slides > section > section > p");
    if (p.length == 0) {
      Display.setTextSlide("Arky arky");
      p = $(".slides > section > section > p");
    }
    p = p[0];
    p.style.fontSize = "" + fontSize + "pt";
    var d = $(".slides > section")[0];
    var lh = parseFloat(_getStyle(p, "line-height"));
    var dh = parseFloat(_getStyle(d, "height"));
    return Math.floor(dh / lh);
  },
  /**
   * Prepare the theme for the next item to be added
   * @param theme The theme to be used
   */
  setTheme: function (theme) {
    if (Display._theme != theme) {
      Display._themeApplied = false;
      Display._theme = theme;
    }
  },
  /**
   * Set background image, replaced when theme is updated/applied
   * @param image_path Image path
   */
  setBackgroundImage: function (image_path) {
    var targetElement = $(".slides > section")[0];
    targetElement.setAttribute("data-background", "url('" + image_path + "')");
    targetElement.setAttribute("data-background-size", "cover");
    Reveal.sync();
  },
  /**
   * Reset/reapply the theme
   */
  resetTheme: function () {
    var targetElement = $(".slides > section")[0];
    if (!targetElement) {
      console.warn("Couldn't reset theme: No slides exist");
      return;
    }
    Display.applyTheme(targetElement, targetElement.classList.contains("text-slides"));
    Reveal.sync();
  },
  /**
   * Apply the theme to the provided element
   * @param targetElement The target element to apply the theme (expected to be a `<section>` in the slides container)
   * @param is_text Used to decide if the main area constraints should be applied
   */
  applyTheme: function (targetElement, is_text=true) {
    Display._themeApplied = true;
    if (!Display._theme) {
      return;
    }
    // Set slide transitions
    var new_transition_type = "none",
        new_transition_speed = "default";
    if (!!Display._theme.display_slide_transition && Display._doTransitions) {
      switch (Display._theme.display_slide_transition_type) {
        case TransitionType.Fade:
          new_transition_type = "fade";
          break;
        case TransitionType.Slide:
          new_transition_type = "slide";
          break;
        case TransitionType.Convex:
          new_transition_type = "convex";
          break;
        case TransitionType.Concave:
          new_transition_type = "concave";
          break;
        case TransitionType.Zoom:
          new_transition_type = "zoom";
          break;
        default:
          new_transition_type = "fade";
      }
      switch (Display._theme.display_slide_transition_speed) {
        case TransitionSpeed.Normal:
          new_transition_speed = "default";
          break;
        case TransitionSpeed.Fast:
          new_transition_speed = "fast";
          break;
        case TransitionSpeed.Slow:
          new_transition_speed = "slow";
          break;
        default:
          new_transition_speed = "default";
      }
      switch (Display._theme.display_slide_transition_direction) {
        case TransitionDirection.Vertical:
          new_transition_type += "-vertical";
          break;
        case TransitionDirection.Horizontal:
        default:
          new_transition_type += "-horizontal";
      }
      if (Display._theme.display_slide_transition_reverse) {
        new_transition_type += "-reverse";
      }
    }
    var slides = targetElement.children;
    for (var i = 0; i < slides.length; i++) {
      slides[i].setAttribute("data-transition", new_transition_type);
      slides[i].setAttribute("data-transition-speed", new_transition_speed);
    }
    // Set the background
    var backgroundContent = "";
    var backgroundHtml = "";
    switch (Display._theme.background_type) {
      case BackgroundType.Transparent:
        backgroundContent = "transparent";
        break;
      case BackgroundType.Solid:
        backgroundContent = Display._theme.background_color;
        break;
      case BackgroundType.Gradient:
        switch (Display._theme.background_direction) {
          case GradientType.Horizontal:
            backgroundContent = _buildLinearGradient("to right",
                                                                 Display._theme.background_start_color,
                                                                 Display._theme.background_end_color);
            break;
          case GradientType.Vertical:
            backgroundContent = _buildLinearGradient("to bottom",
                                                                 Display._theme.background_start_color,
                                                                 Display._theme.background_end_color);
            break;
          case GradientType.LeftTop:
            backgroundContent = _buildLinearGradient("to right bottom",
                                                                 Display._theme.background_start_color,
                                                                 Display._theme.background_end_color);
            break;
          case GradientType.LeftBottom:
            backgroundContent = _buildLinearGradient("to top right",
                                                                 Display._theme.background_start_color,
                                                                 Display._theme.background_end_color);
            break;
          case GradientType.Circular:
            backgroundContent = _buildRadialGradient(window.innerWidth / 2, Display._theme.background_start_color,
                                                                 Display._theme.background_end_color);
            break;
          default:
            backgroundContent = "#000";
        }
        break;
      case BackgroundType.Image:
        backgroundContent = "url('" + Display._getFileUrl(Display._theme.background_filename) + "')";
        break;
      case BackgroundType.Video:
        // never actually used since background type is overridden from video to transparent in window.py
        backgroundContent = Display._theme.background_border_color;
        backgroundHtml = "<video loop autoplay muted><source src='" + Display._getFileUrl(Display._theme.background_filename) + "'></video>";
        break;
      default:
        backgroundContent = "#000";
    }
    targetElement.style.cssText = "";
    targetElement.setAttribute("data-background", backgroundContent);
    targetElement.setAttribute("data-background-size", "cover");

    // set up the main area
    if (!is_text) {
      // only transition and background for non text slides
      return;
    }

    // The main area geometry has to be applied via a stylesheet rule rather than
    // inline styles: Reveal's layout() clears the inline "top" of every section
    // (center is disabled), which would silently discard the theme's Y position.
    // "!important" keeps the theme's boundaries authoritative over Reveal's own
    // section rules (width: 100%, stack height: 100%).
    _createStyle(".reveal .slides > section.text-slides", {
      top: `${Display._theme.font_main_y}px !important`,
      left: `${Display._theme.font_main_x}px !important`,
      width: `${Display._theme.font_main_width}px !important`,
      height: `${Display._theme.font_main_height}px !important`
    }, "main-area-geometry");

    var mainStyle = {
      color: Display._theme.font_main_color,
      "font-family": Display._theme.font_main_name,
      "font-size": `${Display._theme.font_main_size}pt`,
      "font-style": Display._theme.font_main_italics ? "italic" : "",
      "font-weight": Display._theme.font_main_bold ? "bold" : "",
      "line-height": `${100 + Display._theme.font_main_line_adjustment}%`,
      "letter-spacing": `${Display._theme.font_main_letter_adjustment}px`,

      "text-align":
        HorizontalAlignCSS[Display._theme.display_horizontal_align] ||
        HorizontalAlignCSS[HorizontalAlign.Center],

      "justify-content":
        VerticalAlignCSS[Display._theme.display_vertical_align] ||
        VerticalAlignCSS[VerticalAlign.Middle],

      "padding-bottom":
        Display._theme.display_vertical_align === VerticalAlign.Bottom ?
        `${Display._theme.font_main_size / 8}px` : "",

      // This section draws the font outline. Previously we used the proprietary -webkit-text-stroke property
      // but it draws the outline INSIDE the text, instead of OUTSIDE, so we had to go back to the old way
      // of using multiple text-shadow rules to fake an outline.
      "text-shadow": [
        ...(
          Display._theme.font_main_outline ?
          _buildTextOutline(Display._theme.font_main_outline_size, Display._theme.font_main_outline_color) :
          []
        ),
        ...(
          Display._theme.font_main_shadow ?
          _buildTextShadow(Display._theme.font_main_shadow_size,
                           Display._theme.font_main_outline ? Display._theme.font_main_outline_size : 0,
                           Display._theme.font_main_shadow_color) :
          []
        )
      ].join(", ")
    };

    targetElement.style.cssText = "";
    for (var mainKey in mainStyle) {
      if (mainStyle.hasOwnProperty(mainKey)) {
        targetElement.style.setProperty(mainKey, mainStyle[mainKey]);
      }
    }

    // Set up the footer
    var footerStyle = {
      width: `${Display._theme.font_footer_width}px`,
      height: `${Display._theme.font_footer_height}px`,
      top: `${Display._theme.font_footer_y}px`,
      left: `${Display._theme.font_footer_x}px`,
      color: Display._theme.font_footer_color,
      "font-family": Display._theme.font_footer_name,
      "font-size": `${Display._theme.font_footer_size}pt`,
      "font-style": Display._theme.font_footer_italics ? "italic" : "",
      "font-weight": Display._theme.font_footer_bold ? "bold" : "",
      "line-height": `${100 + Display._theme.font_footer_line_adjustment}%`,
      "letter-spacing": `${Display._theme.font_footer_letter_adjustment}px`,
      "white-space": Display._theme.font_footer_wrap ? "normal" : "nowrap",

      "text-align":
        HorizontalAlignCSS[Display._theme.display_horizontal_align_footer] ||
        HorizontalAlignCSS[HorizontalAlign.Left],

      "justify-content":
        VerticalAlignCSS[Display._theme.display_vertical_align_footer] ||
        VerticalAlignCSS[VerticalAlign.Top],

      "padding-bottom":
        Display._theme.display_vertical_align_footer === VerticalAlign.Bottom ?
        `${Display._theme.font_main_size / 8}px` : ""
    };

    for (var footerKey in footerStyle) {
      if (footerStyle.hasOwnProperty(footerKey)) {
        Display._footerContainer.style.setProperty(footerKey, footerStyle[footerKey]);
      }
    }
  },
  /**
   * Called whenever openlp wants to finish completely with the current text/image slides
   * because a different window (eg presentation or media is going to be displaying the next item
   * and we don't want any flashbacks to the current slide contents
   */
  finishWithCurrentItem: function () {
    Display.setTextSlide('');
    var documentBody = $("body")[0];
    documentBody.style.opacity = 1;
    Display._skipNextTransition = true;
    displayWatcher.pleaseRepaint();
  },
  /**
   * Return the video types supported by the video tag
   */
  getVideoTypes: function () {
    var videoElement = document.createElement('video');
    var videoTypes = [];
    if (videoElement.canPlayType('video/mp4; codecs="mp4v.20.8"') == "probably" ||
        videoElement.canPlayType('video/mp4; codecs="avc1.42E01E"') == "pobably" ||
        videoElement.canPlayType('video/mp4; codecs="avc1.42E01E, mp4a.40.2"') == "probably") {
      videoTypes.push(['video/mp4', '*.mp4']);
    }
    if (videoElement.canPlayType('video/ogg; codecs="theora"') == "probably") {
      videoTypes.push(['video/ogg', '*.ogv']);
    }
    if (videoElement.canPlayType('video/webm; codecs="vp8, vorbis"') == "probably") {
      videoTypes.push(['video/webm', '*.webm']);
    }
    return videoTypes;
  },
  /**
   * Sets the scale of the page - used to make preview widgets scale
   */
  setScale: function(scale) {
    document.body.style.zoom = scale+"%";
  },
  /**
   * In order to check if a font exists, we need a container to do
   * calculations on. This method creates that container and caches
   * some width values so that we don't have to do this step every
   * time we check if a font exists.
   */
  _prepareFontContainer: function() {
    Display._fontContainer = document.createElement("span");
    Display._fontContainer.id = "does-font-exist";
    Display._fontContainer.innerHTML = Array(100).join("wi");
    Display._fontContainer.style.cssText = [
      "position: absolute",
      "width: auto",
      "font-size: 128px",
      "left: -999999px"
    ].join(" !important;");
    document.body.appendChild(Display._fontContainer);
  },
  /**
   * Prepare the slide number (slide x/y) for insertion into the Reveal footer
   * This is a callback function which Reveal calls to get the values
   * Fixes https://gitlab.com/openlp/openlp/-/issues/942
   */
  setFooterSlideNumbers: function (slide) {
    let value = ['', '', ''];
    // Reveal does call this function passing undefined
    if (typeof slide === 'undefined') {
      return value;
    }
    value[0] = Reveal.getSlidePastCount(slide) + 1;
    value[1] = '/';
    value[2] = Object.keys(Display._slides).length;
    return value;
  },
  /**
   * Translates file:// protocol URLs to openlp-library://local-file/ scheme
   */
  _getFileUrl: function(url) {
    if (url && (url.indexOf('file://') === 0)) {
      return url.replace('file://', 'openlp-library://local-file/');
    }
    return url;
  },
};

Display._handleNativeCall = (action, ...values) => {
  if (Display[action]) {
    return Display[action](...values);
  }
};

initCommunicationBridge();
communicationBridge.setDisplayTarget(Display);
