-- Create tables

CREATE TABLE public.emissions_report (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    date DATE NOT NULL,
    total_emissions_cache DOUBLE PRECISION NULL
);

CREATE TABLE public.emissions_reductionstrategy (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE public.emissions_report_reduction_strategies (
    id SERIAL PRIMARY KEY,
    report_id INTEGER NOT NULL,
    reductionstrategy_id BIGINT NOT NULL,
    CONSTRAINT emissions_report_reduc_report_id_reductionstrategy_id_key UNIQUE (report_id, reductionstrategy_id),
    CONSTRAINT emissions_report_reduc_report_id_fkey FOREIGN KEY (report_id) 
        REFERENCES public.emissions_report(id) DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT emissions_report_reduc_reductionstrategy_id_fkey FOREIGN KEY (reductionstrategy_id) 
        REFERENCES public.emissions_reductionstrategy(id) DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE public.emissions_source (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(20) NOT NULL,
    description VARCHAR(250) NOT NULL,
    method VARCHAR(20) NOT NULL,
    emission_factor DOUBLE PRECISION NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    value_unit VARCHAR(10) NOT NULL,
    quantity INTEGER NOT NULL,
    lifetime INTEGER NOT NULL,
    acquisition_year INTEGER NOT NULL,
    uncertainty DOUBLE PRECISION NOT NULL,
    report_id INTEGER NOT NULL,
    year INTEGER NULL,
    CONSTRAINT emissions_source_report_id_fkey FOREIGN KEY (report_id)
        REFERENCES public.emissions_report(id) DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE public.emissions_modification (
    id SERIAL PRIMARY KEY,
    modification_type VARCHAR(5) NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    "order" INTEGER NOT NULL,
    start_year SMALLINT NOT NULL,
    end_year SMALLINT NULL,
    source_id BIGINT NOT NULL,
    reduction_strategy_id BIGINT NOT NULL,
    is_progressive BOOLEAN NOT NULL,
    target_value DOUBLE PRECISION NULL,
    calculation_year SMALLINT NULL,
    CONSTRAINT emissions_modification_source_id_fkey FOREIGN KEY (source_id)
        REFERENCES public.emissions_source(id) DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT emissions_modification_reduction_strategy_id_fkey FOREIGN KEY (reduction_strategy_id)
        REFERENCES public.emissions_reductionstrategy(id) DEFERRABLE INITIALLY DEFERRED
);

-- Insert sample data

INSERT INTO public.emissions_report (id, name, date, total_emissions_cache) VALUES
(1, '2023 Emissions Report', '2023-01-01', NULL);

INSERT INTO public.emissions_reductionstrategy (id, name, created_at) VALUES
(1, '2024 Emissions Reduction Plan', '2024-08-12 14:55:05.749824+02');

INSERT INTO public.emissions_report_reduction_strategies (id, report_id, reductionstrategy_id) VALUES
(1, 1, 1);

INSERT INTO public.emissions_source (id, name, category, description, method, emission_factor, value, value_unit, quantity, lifetime, acquisition_year, uncertainty, report_id, year) VALUES
(1, 'EV Fleet', 'TRANSPORT', 'Company Electric Vehicle Fleet (5x Tesla Model Y)', 'DISTANCE', 0.1, 20000, 'km', 5, 10, 2023, 5, 1, NULL),
(2, 'Office Energy', 'ENERGY', 'Office Building Energy Consumption', 'CONSUMPTION', 0.5, 100000, 'kWh', 1, 30, 2020, 3, 1, NULL),
(3, 'Employee Laptops', 'IT', 'Standard Issue Employee Laptops', 'SPEND', 300, 1, 'USD', 100, 4, 2022, 10, 1, NULL);

INSERT INTO public.emissions_modification (id, modification_type, value, "order", start_year, end_year, source_id, reduction_strategy_id, is_progressive, target_value, calculation_year) VALUES
(1, 'VALUE', 0.9, 1, 2024, NULL, 1, 1, false, NULL, 2024),
(2, 'EF', 0.4, 1, 2024, 2026, 2, 1, false, NULL, 2024);

-- Reset sequences

SELECT setval('public.emissions_report_id_seq', (SELECT MAX(id) FROM public.emissions_report));
SELECT setval('public.emissions_reductionstrategy_id_seq', (SELECT MAX(id) FROM public.emissions_reductionstrategy));
SELECT setval('public.emissions_report_reduction_strategies_id_seq', (SELECT MAX(id) FROM public.emissions_report_reduction_strategies));
SELECT setval('public.emissions_source_id_seq', (SELECT MAX(id) FROM public.emissions_source));
SELECT setval('public.emissions_modification_id_seq', (SELECT MAX(id) FROM public.emissions_modification));