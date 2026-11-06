# Progresso do MCC para iSH

Painel visual: [progress/index.html](progress/index.html).
Os marcos atuais do painel são mantidos em [progress/progress.json](progress/progress.json),
com percentuais calculados automaticamente. Este documento preserva o registro narrativo
desta etapa; futuras atualizações dos marcos devem ser feitas no JSON.

Atualizado em: 2026-11-05 (America/Sao_Paulo).

## Painel atual

**Marcos técnicos verificados: 8 de 16, 50%.**

```text
Validação dos marcos     [##########..........] 50% (8/16)
Execução no iSH real     [....................] ainda não testada
```

Esse percentual conta os marcos abaixo com peso igual. Não mede linhas de código,
quantidade de funcionalidades do Minecraft ou porcentagem do cliente moderno portada.
É possível passar de 50% sem estar pronto para uso no iPhone: os marcos restantes
incluem os testes mais importantes no ambiente de destino e na autenticação real.

| Marco | Estado | Evidência atual |
| --- | --- | --- |
| 1. Compilar o cliente de compatibilidade para net40/x86 | Verificado | SDK build: 0 erros, 0 avisos |
| 2. Iniciar o executável real | Verificado no Windows | `--help` executado em diretório temporário |
| 3. Carregar configuração persistida | Verificado no Windows | INI temporário usado pelo teste de rede |
| 4. Conectar e realizar handshake/login Java | Verificado em endpoint controlado | Cliente real, protocolo 47 / 1.8.9 |
| 5. Receber chat comprimido | Verificado no Windows | Marcador recebido no stdout |
| 6. Enviar chat pelo terminal | Verificado no Windows | Endpoint confirmou o pacote enviado por stdin |
| 7. Responder keep-alive | Verificado no Windows | Endpoint confirmou resposta com identificador esperado |
| 8. Encerrar por comando interativo | Verificado no Windows | `/exit`, processo encerrado com código 0 |
| 9. Compilar usando Mono no Alpine x86 | Pendente | Workflow criado, ainda sem resultado observado |
| 10. Iniciar o cliente dentro do iSH real | Pendente | Sem dispositivo iSH acessível nesta sessão |
| 11. Instalar e iniciar via `sh run.sh` no destino | Pendente | Scripts passaram em `sh -n`; execução no destino falta |
| 12. Concluir OAuth Microsoft em conta real | Pendente | Prompt e rejeição de código inválido testados; sucesso não testado |
| 13. Validar propriedade/perfil com conta real | Pendente | Implementação upstream preservada, falta teste real |
| 14. Manter sessão online com criptografia | Pendente | Código preservado, teste de rede atual usa servidor local offline |
| 15. Renovar token de conta real | Pendente | Código preservado e parâmetros escapados, falta teste real |
| 16. Medir estabilidade, memória e tempo no iSH | Pendente | Ainda sem medição no dispositivo |

## Quanto já foi portado

Existe um **cliente MCC histórico real compilável**, com login/handshake de protocolo,
chat, compressão, keep-alive, configuração, bots e scripts da base histórica.
O caminho de autenticação Microsoft foi adaptado para abrir o login no navegador,
sem solicitar senha no terminal. O caminho online completo ainda precisa ser validado.

A base selecionada declara Minecraft **1.4.6 a 1.18.2**. O teste de integração atual
exercita **1.8.9**, incluindo compressão com limiar 1 e limiar 0. Não há evidência
de teste para cada versão da faixa. O suporte moderno até 26.2 do projeto principal
não faz parte deste runtime de compatibilidade neste momento.

## Linha do tempo

Todos os eventos abaixo ocorreram em 2026-11-05 no fuso local. São etapas observadas,
sem horários ou estimativas retroativos.

1. **Instruções e repositório:** lido `INSTRUÇÕES.txt`, confirmado o origin
   `JuninSB/mcc-ios`; arquivo de instruções excluído pelo `.gitignore`.
2. **Análise:** confirmado net10.0 no cliente moderno e identificadas dependências
   incompatíveis com um simples retarget para Mono. Confirmado que WSL está desativado.
3. **Escolha técnica:** localizada a branch histórica `previous`, commit
   `b3cc2351ee14d8e4fadc6f0e6115478872143c48`, com .NET Framework 4.0 e protocolos até 1.18.2.
4. **Base importada:** adicionado somente o runtime histórico em `ports/ish`,
   preservando o código principal e registrando a procedência.
5. **Entrada de execução:** criados `run.sh`, `install.sh` e diagnóstico;
   os três passaram na verificação de sintaxe POSIX.
6. **Primeira compilação:** corrigidas a inclusão indevida de scripts de exemplo
   e a referência ausente a Microsoft.CSharp. O executável real iniciou com `--help`.
7. **Compatibilidade e privacidade:** login por navegador, leitura de URL de retorno,
   parâmetros OAuth escapados, remoção de impressão de token e do watcher de cache.
8. **Primeira integração funcional:** teste com endpoint controlado confirmou handshake,
   login, chat comprimido nos dois sentidos, keep-alive e `/exit`.
9. **Correções encontradas em teste:** corrigidos limiar zero da compressão,
   leitura de teclado incompatível com BasicIO e tratamento de EOF.
10. **Autenticação negativa:** Microsoft rejeitou código deliberadamente inválido;
    o cliente mostrou erro compreensível, não solicitou senha e encerrou sem a exceção
    de Console.KeyAvailable encontrada na primeira execução.
11. **Documentação e automação:** criados README-iSH.md, PORTING.md e workflow Alpine
    x86. Nenhum resultado de CI foi observado até esta atualização.

## Arquivos e mudanças

| Área | Arquivos | Mudança |
| --- | --- | --- |
| Execução | `run.sh`, `install.sh` | Dependências via apk, build Mono e estado privado por usuário |
| Diagnóstico | `scripts/diagnose-ish.sh` | Informações de plataforma e disponibilidade do runtime |
| Runtime | `ports/ish/MinecraftClient/` | Base histórica e adaptações de compatibilidade |
| Build | `ports/ish/MinecraftClient/Build.csproj` | Compilação net40/x86 em host com SDK |
| Autenticação | `Program.cs`, `ProtocolHandler.cs`, `MicrosoftAuthentication.cs` dentro do porte | Navegador, URL de retorno, erros e proteção de tokens |
| Cache | `Protocol/Session/SessionCache.cs` dentro do porte | Removida dependência de watcher para sincronizar cache |
| Rede/terminal | `Protocol18.cs`, `McClient.cs` dentro do porte | Compressão com limiar zero e EOF |
| Tradução | `Translations.resx`, `Translations.Designer.cs` dentro do porte | Novas mensagens localizáveis |
| Testes | `tests/ish_network.py`, `tests/ish_auth.py` | Integração com executável real e falha OAuth sem credenciais |
| CI | `.github/workflows/ish.yml` | Build/testes planejados em Alpine x86 com Mono |
| Documentação | `README-iSH.md`, `PORTING.md`, `ports/ish/UPSTREAM.md` | Uso, evidências, procedência e limites |
| Publicação | `.gitignore` | Exclusão de INSTRUÇÕES.txt |

## Próximos marcos

1. Executar o build Mono e os testes no Alpine x86; corrigir os resultados reais.
2. Completar os avisos de licença das bibliotecas incorporadas antes de distribuir.
3. Validar criptografia, renovação de token e falhas de conexão.
4. Executar o diagnóstico e o cliente em iSH real; medir recursos.
5. Validar uma sessão Microsoft legítima e um servidor online compatível.

Não houve push nesta etapa. O arquivo de instruções continua fora do versionamento.
Atualizar este painel somente com evidências novas; não aumentar o percentual por
tempo gasto, quantidade de arquivos ou existência de código ainda não executado.
