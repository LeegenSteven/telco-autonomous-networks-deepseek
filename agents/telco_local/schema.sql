CREATE TABLE IF NOT EXISTS incidents (
    incident_id VARCHAR PRIMARY KEY,
    enodeb_id VARCHAR,
    cell_id VARCHAR,
    start_ts TIMESTAMP NOT NULL,
    end_ts TIMESTAMP,
    status VARCHAR NOT NULL,
    description VARCHAR NOT NULL,
    kpi_missed JSON NOT NULL,
    preliminary_analysis VARCHAR,
    severity VARCHAR,
    events VARCHAR,
    cause VARCHAR,
    final_analysis VARCHAR,
    resolution VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_events (
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    agent VARCHAR,
    event_type VARCHAR,
    status VARCHAR,
    details JSON
);

CREATE OR REPLACE VIEW performance_kpi AS
SELECT
    enodeb_id,
    cell_id,
    measurement_end,
    (
        ERAB_EstabInitSuccNbr_QCI1 +
        ERAB_EstabInitSuccNbr_QCI2 +
        ERAB_EstabInitSuccNbr_QCI3 +
        ERAB_EstabInitSuccNbr_QCI4 +
        ERAB_EstabInitSuccNbr_QCI5 +
        ERAB_EstabInitSuccNbr_QCI6 +
        ERAB_EstabInitSuccNbr_QCI7 +
        ERAB_EstabInitSuccNbr_QCI8 +
        ERAB_EstabInitSuccNbr_QCI9
    ) * 100.0 / NULLIF(
        ERAB_EstabInitAttNbr_QCI1 +
        ERAB_EstabInitAttNbr_QCI2 +
        ERAB_EstabInitAttNbr_QCI3 +
        ERAB_EstabInitAttNbr_QCI4 +
        ERAB_EstabInitAttNbr_QCI5 +
        ERAB_EstabInitAttNbr_QCI6 +
        ERAB_EstabInitAttNbr_QCI7 +
        ERAB_EstabInitAttNbr_QCI8 +
        ERAB_EstabInitAttNbr_QCI9,
        0
    ) AS erab_success_rate,
    (
        ERAB_RelActNbr_QCI1 +
        ERAB_RelActNbr_QCI2 +
        ERAB_RelActNbr_QCI3 +
        ERAB_RelActNbr_QCI4 +
        ERAB_RelActNbr_QCI5 +
        ERAB_RelActNbr_QCI6 +
        ERAB_RelActNbr_QCI7 +
        ERAB_RelActNbr_QCI8 +
        ERAB_RelActNbr_QCI9
    ) * 3600.0 / NULLIF(ERAB_SessionTimeUE, 0) AS retainability
FROM performance;
