# Painel do porte

Abra a partir da raiz do repositório:

```sh
python3 -m http.server 8000 --bind 127.0.0.1 --directory progress
```

No Windows, use `py -3` no lugar de `python3`. Acesse http://127.0.0.1:8000.
Para encerrar o servidor, use Ctrl+C. Nenhum pacote adicional ou serviço externo é necessário.
O servidor expõe somente a pasta do painel, não o repositório ou os tokens do cliente.

O HTML também abre diretamente: escolha `progress.json` pelo botão de arquivo.
Nesse modo, selecione novamente o arquivo depois de editá-lo, pois o navegador
não permite leitura automática de arquivos locais por fetch.

## Atualização

**Edite somente `progress.json` para atualizar o painel.**

* `milestones`: marcos com `id` único, `group`, `title`, `status`, `scope`, `evidence` e `artifact`.
* `status`: `verified` quando houver teste comprovando o marco; `pending` nos demais casos.
* `scope`: ambiente do teste. Nunca trate teste no Windows como teste em iSH.
* `groups`: categorias e ordem de apresentação.
* `timeline`: eventos com data ISO `AAAA-MM-DD`, título e descrição, na ordem em que ocorreram.
  A página exibe do mais recente para o mais antigo e conserva a ordem inversa para o mesmo dia.
* `updated` e `revision`: data dos dados e identificador da atualização. Não são datas de testes inventadas.
* `target`, `versions`, `nextSteps`, `summary`: situação do destino, versões, próximos passos e resumo.

O percentual geral e os percentuais por categoria são calculados automaticamente:
marcos `verified` divididos pelo total de marcos, com peso igual e arredondamento ao inteiro.
Não há campo de porcentagem manual. Adicionar marcos aumenta o denominador; registre
mudanças de escopo na linha do tempo para manter comparações honestas.

Via HTTP, a página busca o JSON sem cache ao abrir, a cada 30 segundos enquanto visível,
ao retornar à aba e ao clicar em Atualizar dados. Se o arquivo estiver inválido ou a rede
falhar, mostra o erro e preserva a última leitura válida. Textos do JSON são exibidos como
texto, não como HTML executável. Não coloque credenciais, tokens ou dados de conta no JSON.

`PROGRESSO.md` é o registro narrativo anterior. Os dados do painel vivem neste JSON;
não há sincronização automática do Markdown. Para acompanhar o porte visualmente,
consulte este painel e mantenha o JSON como fonte de verdade dos marcos.
