# Estratégia futura de orquestração

Prefect é o padrão adotado pela Base dos Dados para a orquestração das
pipelines deste projeto. Nesta fase de preparação ele não é dependência do
pacote, não é instalado no CI e não há infraestrutura de orquestração.

A adoção ocorrerá quando os primeiros fluxos reais forem desenhados pelos
engenheiros responsáveis. Airflow, MWAA ou outro orquestrador não devem ser
introduzidos sem nova decisão arquitetural.
