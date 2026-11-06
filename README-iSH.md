# MCC para iSH

**Escopo requerido: porte completo do MCC atual.** O runtime em `ports/ish` é o
protótipo parcial já testado, não a entrega final. TUI/minimapa, inventário, mundo,
movimento, todos os comandos/bots, scripts e integrações estão no escopo obrigatório.
O inventário completo e os bloqueios medidos ficam em `progress/full-scope.json`
e `ports/full/ASSESSMENT.md`. O percentual antigo do núcleo não mede o porte integral.

Porte de compatibilidade do MCC histórico para Mono e Alpine Linux **x86 de 32 bits**.
Destinado a executar o cliente localmente no iPhone, sem SSH, VPS ou computador durante
o uso. A execução em iSH real ainda precisa de validação.
Esta versão mantém os protocolos 1.4.6 a 1.18.2 da base histórica e adiciona um caminho
experimental de console para 1.21.11, selecionado explicitamente com `--mcversion=1.21.11`.

O executável principal foi testado no Windows e no Alpine 3.22.8 x86 com Mono contra
o Paper 1.21.11 do usuário: entrada, comando, chat com eco e saída passaram. Esse caminho ainda não tem assinatura
de chat, bots, inventário, mundo ou reconexão automática e não foi validado no iSH.
Servidores que exigem chat assinado não permitem envio pelo caminho atual.

## Instalação e uso

No iSH, com o repositório `community` da mesma versão do Alpine habilitado:

```sh
apk update
apk add git
git clone --branch ish-port --single-branch https://github.com/JuninSB/mcc-ios.git
cd mcc-ios
sh run.sh
```

O primeiro início instala `mono` e `ca-certificates` disponíveis no seu repositório
e compila com `xbuild`. Não altera os repositórios do sistema. Mono ocupa centenas
de MB e a compilação sob emulação pode demorar. Alpine 3.22 fornece Mono para x86;
a compatibilidade com a versão do Alpine fornecida pelo seu iSH deve ser verificada.
No Alpine 3.22.8 x86, Mono 6.14.1 passou no build, protocolo, criptografia, TLS e
rejeição OAuth. Nenhuma versão do iSH foi validada em dispositivo até agora.
A branch de teste contém código e documentação; o workflow de CI permanece local
até a permissão GitHub `workflow` estar disponível.

O cliente mostra um link: abra no Safari, entre na Microsoft e cole o código de
autorização ou a URL de retorno completa. Nunca informe a senha na linha de comando.
É necessária uma conta com Minecraft Java. A autenticação mantém as verificações
Xbox Live, propriedade do jogo, perfil e sessão. Login bem-sucedido em conta real
ainda está pendente de validação. Não há fluxo device-code nesta implementação.

Informe o endereço do servidor quando solicitado. Mensagens são enviadas pelo terminal;
comandos de servidor começam com `/`. `/quit` desconecta e `/exit` encerra.

```sh
sh run.sh --help
sh run.sh --serverip=servidor.exemplo:25565 --mcversion=1.18.2
sh run.sh --serverip=servidor.exemplo:25565 --mcversion=1.21.11
sh scripts/diagnose-ish.sh
```

Configuração e tokens ficam em `$HOME/.config/mcc-ish` (diretório 700, novos arquivos
privados via umask 077). Personalize com `MCC_ISH_HOME`. Tokens ficam em texto simples
privado, não são criptografados em repouso. Não compartilhe `SessionCache.ini`.
A configuração é INI do MCC histórico, não TOML do cliente moderno.
Ative reconexão na seção AutoRelog do INI; ajuste verbosidade na seção Logging.

Para atualizar, execute `git pull` e `MCC_ISH_REBUILD=1 sh install.sh`.
O runtime não recompila automaticamente a cada inicialização.

## Limitações e diagnóstico

* `mono` ausente: habilite `community` para a versão instalada, execute `apk update`
  e `apk add mono ca-certificates`. Não misture versões ou arquiteturas.
* Erro TLS: confira data/hora e certificados. Não desative validação de certificado.
* Falha OAuth: gere um novo código, confira rede e os serviços Microsoft.
* Servidor moderno: use uma versão suportada ou um servidor com tradução de protocolo compatível.
* Biblioteca nativa ou syscall não suportada: execute o diagnóstico e guarde o erro completo.
* O iOS pode suspender o aplicativo em segundo plano. Mantenha o iSH em primeiro plano.
* Edição avançada de linha/TUI moderna, MCP e integrações modernas não foram portadas.
  Bots e scripts da base histórica permanecem; não foram validados individualmente.
* Terreno, entidades e inventário elevam o consumo. Comece com os padrões conservadores.

Resultados verificáveis, licenças e pendências estão em [PORTING.md](PORTING.md).
