'use strict';

(() => {
  const $ = id => document.getElementById(id);
  let data = null;
  let filter = 'all';
  let loading = false;
  let localFile = false;
  const states = { verified: 'Verificado', pending: 'Pendente' };

  function element(tag, className, value) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (value !== undefined) node.textContent = value;
    return node;
  }

  function validate(value) {
    const fail = () => { throw new Error('Arquivo de progresso inválido. Confira a estrutura e os estados dos marcos.'); };
    const text = item => typeof item === 'string' && item.trim().length > 0;
    const date = item => text(item) && /^\d{4}-\d{2}-\d{2}$/.test(item) && !Number.isNaN(Date.parse(item));
    if (!value || value.schemaVersion !== 1 || !date(value.updated)) fail();
    for (const key of ['revision', 'status', 'summary', 'methodology', 'why']) if (!text(value[key])) fail();
    if (!value.target || !['status', 'detail', 'note'].every(k => text(value.target[k]))) fail();
    if (!value.versions || !['tested', 'detail'].every(k => text(value.versions[k]))) fail();
    for (const key of ['groups', 'milestones', 'nextSteps', 'timeline', 'environment', 'sources']) {
      if (!Array.isArray(value[key]) || !value[key].length) fail();
    }
    if (!value.nextSteps.every(text) || !value.environment.every(text)) fail();
    const groups = new Set();
    for (const group of value.groups) {
      if (!text(group.id) || !text(group.title) || groups.has(group.id)) fail();
      groups.add(group.id);
    }
    const ids = new Set();
    for (const milestone of value.milestones) {
      if (!['id', 'group', 'title', 'scope', 'evidence', 'artifact'].every(k => text(milestone[k])) ||
          !Object.hasOwn(states, milestone.status) || !groups.has(milestone.group) || ids.has(milestone.id)) fail();
      ids.add(milestone.id);
    }
    for (const event of value.timeline) {
      if (!date(event.date) || !text(event.title) || !text(event.detail)) fail();
    }
    for (const source of value.sources) {
      if (!text(source.label) || !text(source.url)) fail();
      let url;
      try { url = new URL(source.url); } catch { fail(); }
      if (url.protocol !== 'https:') fail();
    }
    return value;
  }

  function renderGroups() {
    const container = $('groups');
    const expanded = new Set([...container.querySelectorAll('details[open]')].map(node => node.dataset.id));
    container.replaceChildren();
    let visible = 0;
    for (const group of data.groups) {
      const all = data.milestones.filter(item => item.group === group.id);
      const items = all.filter(item => filter === 'all' || item.status === filter);
      if (!items.length) continue;
      visible += items.length;
      const section = element('section', 'group');
      const heading = element('div', 'group-heading');
      const done = all.filter(item => item.status === 'verified').length;
      heading.append(element('h3', '', group.title), element('span', '', `${done}/${all.length} verificados · ${Math.round(done / all.length * 100)}%`));
      section.append(heading);
      const list = element('div', 'milestone-list');
      for (const item of items) {
        const detail = element('details', 'milestone');
        detail.dataset.id = item.id;
        detail.open = expanded.has(item.id);
        const summary = element('summary');
        const check = element('span', item.status === 'verified' ? 'check' : 'check waiting', item.status === 'verified' ? '✓' : '·');
        check.setAttribute('aria-hidden', 'true');
        const chevron = element('span', 'chevron', '›');
        chevron.setAttribute('aria-hidden', 'true');
        summary.append(check, element('span', 'milestone-title', item.title), element('span', `status ${item.status}`, states[item.status]), chevron);
        const evidence = element('div', 'evidence');
        evidence.append(element('span', 'scope', item.scope), element('p', '', item.evidence), element('code', '', item.artifact));
        detail.append(summary, evidence);
        list.append(detail);
      }
      section.append(list);
      container.append(section);
    }
    $('empty').hidden = visible > 0;
  }

  function render() {
    const verified = data.milestones.filter(item => item.status === 'verified').length;
    const total = data.milestones.length;
    const percent = Math.round(verified / total * 100);
    $('revision').textContent = data.revision;
    $('summary').textContent = data.summary;
    $('project-status').textContent = data.status;
    $('percent').textContent = `${percent}%`;
    $('count').textContent = `${verified} de ${total} marcos`;
    $('progress-fill').style.width = `${percent}%`;
    $('overall-progress').setAttribute('aria-valuenow', String(percent));
    $('overall-progress').setAttribute('aria-valuetext', `${verified} de ${total} marcos verificados`);
    $('methodology').textContent = data.methodology;
    $('target-status').textContent = data.target.status;
    $('target-detail').textContent = data.target.detail;
    $('target-note').textContent = data.target.note;
    $('tested-version').textContent = data.versions.tested;
    $('versions-detail').textContent = data.versions.detail;
    $('why').textContent = data.why;
    $('environment').replaceChildren(...data.environment.map(item => element('span', '', item)));
    $('next-steps').replaceChildren(...data.nextSteps.map(item => element('li', '', item)));
    $('sources').replaceChildren(...data.sources.map(source => {
      const link = element('a', '', source.label);
      link.href = source.url;
      return link;
    }));
    $('timeline-items').replaceChildren(...data.timeline.map((event, index) => ({...event, index}))
      .sort((a, b) => b.date.localeCompare(a.date) || b.index - a.index)
      .map(event => {
        const article = element('article', 'event');
        const time = element('time', '', new Intl.DateTimeFormat('pt-BR', {dateStyle: 'medium', timeZone: 'UTC'}).format(new Date(`${event.date}T12:00:00Z`)));
        time.dateTime = event.date;
        const body = element('div');
        body.append(element('h3', '', event.title), element('p', '', event.detail));
        article.append(time, body);
        return article;
      }));
    $('updated').textContent = `Dados atualizados em ${data.updated.split('-').reverse().join('/')} · ${data.revision}`;
    renderGroups();
  }

  function showError(message) {
    $('notice').hidden = false;
    $('notice').textContent = message;
    $('sync-status').textContent = data ? 'Falha ao atualizar. Exibindo a última leitura válida.' : 'Não foi possível carregar os dados.';
  }

  async function load() {
    if (loading || localFile) return;
    if (location.protocol === 'file:') {
      $('file-controls').hidden = false;
      $('refresh').disabled = true;
      showError('Para leitura automática, abra este painel por um servidor local. Você também pode selecionar progress.json abaixo.');
      return;
    }
    loading = true;
    $('refresh').disabled = true;
    try {
      const response = await fetch('./progress.json', {cache: 'no-store', signal: AbortSignal.timeout(10000)});
      if (!response.ok) throw new Error(`Leitura falhou (HTTP ${response.status}).`);
      const next = validate(await response.json());
      if (JSON.stringify(next) !== JSON.stringify(data)) {
        data = next;
        render();
      }
      $('notice').hidden = true;
      $('sync-status').textContent = `Sincronizado às ${new Date().toLocaleTimeString('pt-BR')} · leitura automática a cada 30 s`;
    } catch (error) {
      showError(`${error.message} Confira se progress.json está disponível e contém JSON válido.`);
    } finally {
      loading = false;
      $('refresh').disabled = false;
    }
  }

  for (const button of document.querySelectorAll('[data-filter]')) {
    button.addEventListener('click', () => {
      filter = button.dataset.filter;
      for (const other of document.querySelectorAll('[data-filter]')) {
        const active = other === button;
        other.classList.toggle('active', active);
        other.setAttribute('aria-pressed', String(active));
      }
      if (data) renderGroups();
    });
  }
  $('refresh').addEventListener('click', load);
  $('file-input').addEventListener('change', async event => {
    const file = event.target.files[0];
    if (!file) return;
    try {
      const next = validate(JSON.parse(await file.text()));
      localFile = true;
      data = next;
      render();
      $('notice').hidden = true;
      $('sync-status').textContent = 'Arquivo local carregado. Selecione-o novamente após editar.';
    } catch (error) { showError(error.message); }
    event.target.value = '';
  });
  document.addEventListener('visibilitychange', () => { if (!document.hidden) load(); });
  setInterval(() => { if (!document.hidden) load(); }, 30000);
  load();
})();
