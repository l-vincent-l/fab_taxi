DO LANGUAGE plpgsql $$
    DECLARE
    ads_v int;
    vehicle_v int;
    driver_v int;
    BEGIN
        SELECT ads_id INTO ads_v FROM taxi where id = '%(taxi_id)s';
        SELECT vehicle_id INTO vehicle_v FROM taxi where id = '%(taxi_id)s';
        SELECT driver_id INTO driver_v FROM taxi where id = '%(taxi_id)s';
        DELETE FROM taxi where id = '%(taxi_id)s';
        DELETE FROM "ADS" where id = ads_v;
        DELETE FROM vehicle_description where vehicle_id = vehicle_v;
        DELETE FROM vehicle where id = vehicle_v;
        DELETE FROM driver where id = driver_v;
    END;
$$;
