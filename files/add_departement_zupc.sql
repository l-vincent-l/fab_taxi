DO LANGUAGE plpgsql $$
    BEGIN
        IF (SELECT COUNT(id)::int FROM departement WHERE nom = 'testing') = 0 THEN 
            INSERT INTO departement (nom, numero) VALUES ('testing', 999);
            RAISE NOTICE 'departement testing has been inserted';
        END IF;
    END;
$$;

DO LANGUAGE plpgsql $$
    DECLARE
    departement_id int;
    zupc_id int;
    BEGIN
        SELECT id INTO departement_id FROM departement WHERE nom='testing';
        IF (SELECT COUNT(id)::int FROM "ZUPC" WHERE nom = 'testing') = 0 THEN 
            INSERT INTO "ZUPC" ("departement_id", "nom", "insee", "shape", active) VALUES (departement_id, 'testing', '999999', ST_geomFROMGEOJSON('{"type": "MultiPolygon","coordinates": [[[[0.0, 0.0], [0.0, 1.0], [1.0, 1.0],[1.0, 0.0], [0.0, 0.0] ]]]}'), true);
            RAISE NOTICE 'zupc testing has been inserted';
        END IF;
        SELECT id INTO zupc_id FROM "ZUPC" where nom = 'testing';
        UPDATE "ZUPC" SET parent_id = zupc_id where id = zupc_id;
    END;
$$;
