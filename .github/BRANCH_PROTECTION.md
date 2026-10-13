# Proteção recomendada para `main`

Aplicar uma ruleset de branch direcionada a `main` com:

- Pull Request obrigatório, com uma aprovação de qualquer pessoa com acesso de
  escrita;
- conversas resolvidas antes do merge;
- aprovação anterior descartada quando novos commits alterarem o PR;
- checks obrigatórios `Python lint` e `Python tests and imports`;
- branch atualizada com `main` antes do merge (`strict status checks`);
- bloqueio de force push e de deleção da branch;
- nenhuma exceção permanente para push direto.

A revisão pelos owners de `.github/CODEOWNERS` não é obrigatória. O GitHub
apenas solicita a revisão deles de forma automática. A aprovação extra para
commits sem atribuição (por exemplo, coautoria de agentes) fica desativada.
Assim, uma única aprovação de qualquer revisor é suficiente.

A ruleset depende de permissão administrativa no GitHub e deve ser conferida
em **Settings → Rules → Rulesets** após sua aplicação.
