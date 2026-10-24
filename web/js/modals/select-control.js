  // ---------------------------------------------------------------------------
  // Custom select (keyboard-accessible listbox)
  // ---------------------------------------------------------------------------

  function SelectMenu(root, config) {
    this.root = root;
    this.options = config.options || [];
    this.searchable = Boolean(config.searchable);
    this.onChange = config.onChange || function () {};
    this.value = config.value !== undefined ? String(config.value) : '';
    this.open = false;
    this.filter = '';
    this.activeIndex = 0;
    this.id = 'select-' + Math.random().toString(36).slice(2, 8);

    root.classList.add('select');
    root.replaceChildren();

    this.trigger = document.createElement('button');
    this.trigger.type = 'button';
    this.trigger.className = 'select-trigger';
    this.trigger.setAttribute('role', 'combobox');
    this.trigger.setAttribute('aria-haspopup', 'listbox');
    this.trigger.setAttribute('aria-expanded', 'false');
    this.trigger.setAttribute('aria-controls', this.id + '-list');
    this.triggerValue = document.createElement('span');
    this.trigger.appendChild(this.triggerValue);
    this.trigger.appendChild(icon('chevron-down'));
    root.appendChild(this.trigger);

    this.popover = document.createElement('div');
    this.popover.className = 'select-popover';
    this.popover.hidden = true;
    root.appendChild(this.popover);

    if (this.searchable) {
      var searchWrap = document.createElement('div');
      searchWrap.className = 'select-search';
      this.searchInput = document.createElement('input');
      this.searchInput.type = 'search';
      this.searchInput.placeholder = 'Search languages';
      this.searchInput.setAttribute('aria-label', 'Search options');
      this.searchInput.addEventListener('input', this.onSearch.bind(this));
      this.searchInput.addEventListener('keydown', this.onSearchKeydown.bind(this));
      searchWrap.appendChild(this.searchInput);
      this.popover.appendChild(searchWrap);
    }

    this.list = document.createElement('div');
    this.list.className = 'select-list';
    this.list.id = this.id + '-list';
    this.list.setAttribute('role', 'listbox');
    this.list.setAttribute('aria-label', config.label || 'Options');
    this.popover.appendChild(this.list);

    this.trigger.addEventListener('click', this.toggle.bind(this));
    this.trigger.addEventListener('keydown', this.onTriggerKeydown.bind(this));
    this.list.addEventListener('keydown', this.onListKeydown.bind(this));
    this.list.addEventListener('click', this.onListClick.bind(this));
    this.setValue(this.value, false);
  }

  SelectMenu.prototype.setOptions = function (options) {
    this.options = options || [];
    this.renderOptions();
  };

  SelectMenu.prototype.labelFor = function (value) {
    for (var i = 0; i < this.options.length; i++) {
      if (String(this.options[i].value) === String(value)) return this.options[i].label;
    }
    return this.options.length ? this.options[0].label : '';
  };

  SelectMenu.prototype.setValue = function (value, notify) {
    var next = String(value);
    var found = this.options.some(function (option) { return String(option.value) === next; });
    if (!found && this.options.length) next = String(this.options[0].value);
    this.value = next;
    this.root.dataset.value = next;
    this.triggerValue.textContent = this.labelFor(next);
    if (notify !== false) this.onChange(next);
  };

  SelectMenu.prototype.toggle = function () {
    if (this.open) this.close();
    else this.openMenu();
  };

  SelectMenu.prototype.openMenu = function () {
    closeAllSelects(this);
    this.open = true;
    this.filter = '';
    this.activeIndex = Math.max(0, this.options.findIndex(function (option) {
      return String(option.value) === this.value;
    }.bind(this)));
    if (this.searchInput) this.searchInput.value = '';
    this.popover.hidden = false;
    this.trigger.setAttribute('aria-expanded', 'true');
    this.renderOptions();
    if (this.searchInput) this.searchInput.focus();
    else this.focusActive();
  };

  SelectMenu.prototype.close = function () {
    this.open = false;
    this.popover.hidden = true;
    this.trigger.setAttribute('aria-expanded', 'false');
    this.trigger.focus();
  };

  SelectMenu.prototype.visibleOptions = function () {
    var filter = this.filter.toLowerCase();
    if (!filter) return this.options;
    return this.options.filter(function (option) {
      return (option.label + ' ' + option.value).toLowerCase().indexOf(filter) >= 0;
    });
  };

  SelectMenu.prototype.renderOptions = function () {
    var self = this;
    var visible = this.visibleOptions();
    if (!visible.length) {
      var empty = document.createElement('div');
      empty.className = 'palette-empty';
      empty.textContent = 'No options match.';
      this.list.replaceChildren(empty);
      return;
    }
    if (this.activeIndex >= visible.length) this.activeIndex = visible.length - 1;
    var fragment = document.createDocumentFragment();
    visible.forEach(function (option, index) {
      var button = document.createElement('button');
      button.type = 'button';
      button.className = 'select-option';
      button.setAttribute('role', 'option');
      button.setAttribute('aria-selected', String(String(option.value) === self.value));
      button.dataset.value = String(option.value);
      button.textContent = option.label;
      if (String(option.value) === self.value) button.appendChild(icon('check'));
      fragment.appendChild(button);
    });
    this.list.replaceChildren(fragment);
    this.focusActive();
  };

  SelectMenu.prototype.focusActive = function () {
    var buttons = this.list.querySelectorAll('.select-option');
    Array.prototype.forEach.call(buttons, function (button, index) {
      var active = index === this.activeIndex;
      button.tabIndex = active ? 0 : -1;
      button.classList.toggle('is-active', active);
    }.bind(this));
    if (!this.searchInput && buttons[this.activeIndex]) buttons[this.activeIndex].focus();
  };

  SelectMenu.prototype.onSearch = function () {
    this.filter = this.searchInput.value;
    this.activeIndex = 0;
    this.renderOptions();
  };

  SelectMenu.prototype.onSearchKeydown = function (event) {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      this.activeIndex = Math.min(this.visibleOptions().length - 1, this.activeIndex + 1);
      this.focusActive();
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      this.activeIndex = Math.max(0, this.activeIndex - 1);
      this.focusActive();
    } else if (event.key === 'Enter') {
      event.preventDefault();
      var options = this.visibleOptions();
      if (options[this.activeIndex]) this.choose(options[this.activeIndex].value);
    } else if (event.key === 'Escape') {
      event.preventDefault();
      event.stopPropagation();
      this.close();
    }
  };

  SelectMenu.prototype.onTriggerKeydown = function (event) {
    if (event.key === 'ArrowDown' || event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      this.openMenu();
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      this.openMenu();
    }
  };

  SelectMenu.prototype.onListKeydown = function (event) {
    var options = this.visibleOptions();
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      this.activeIndex = Math.min(options.length - 1, this.activeIndex + 1);
      this.focusActive();
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      this.activeIndex = Math.max(0, this.activeIndex - 1);
      this.focusActive();
    } else if (event.key === 'Home') {
      event.preventDefault();
      this.activeIndex = 0;
      this.focusActive();
    } else if (event.key === 'End') {
      event.preventDefault();
      this.activeIndex = options.length - 1;
      this.focusActive();
    } else if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      if (options[this.activeIndex]) this.choose(options[this.activeIndex].value);
    } else if (event.key === 'Escape') {
      event.preventDefault();
      event.stopPropagation();
      this.close();
    } else if (event.key === 'Tab') {
      this.close();
    }
  };

  SelectMenu.prototype.onListClick = function (event) {
    var button = event.target.closest('.select-option');
    if (!button) return;
    this.choose(button.dataset.value);
  };

  SelectMenu.prototype.choose = function (value) {
    this.setValue(value, true);
    this.close();
  };

  function closeAllSelects(except) {
    [langSelectInstance, sleepSelectInstance].forEach(function (instance) {
      if (instance && instance !== except && instance.open) {
        instance.open = false;
        instance.popover.hidden = true;
        instance.trigger.setAttribute('aria-expanded', 'false');
      }
    });
  }

  var langSelectInstance = null;
  var sleepSelectInstance = null;

  function initSelects() {
    langSelectInstance = new SelectMenu(el.langSelect, {
      label: 'Translation language',
      searchable: true,
      value: AppState.settings.target_lang,
      options: LANGS.map(function (entry) { return { value: entry[0], label: entry[1] + ' (' + entry[0].toUpperCase() + ')' }; }),
      onChange: function (value) { setTargetLanguage(value, true); }
    });
    sleepSelectInstance = new SelectMenu(el.sleepSelect, {
      label: 'Sleep timer',
      value: '0',
      options: [
        { value: '0', label: 'Off' },
        { value: '15', label: '15 minutes' },
        { value: '30', label: '30 minutes' },
        { value: '45', label: '45 minutes' },
        { value: '60', label: '60 minutes' },
        { value: '90', label: '90 minutes' }
      ],
      onChange: function (value) { setSleepTimer(Number(value)); }
    });
  }

