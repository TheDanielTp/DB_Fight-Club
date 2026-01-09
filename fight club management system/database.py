import os
from datetime import datetime, date
import psycopg2
from psycopg2 import Error
from psycopg2.extras import RealDictCursor
from typing import cast

class Database:
    def __init__(self):
        self.db_uri = os.environ.get("DB_URI")

        if not self.db_uri:
            raise ValueError("Database URI was not found.")
        
    def get_connection(self):
        try:
            return psycopg2.connect(self.db_uri, cursor_factory=RealDictCursor)
        except Error as e:
            print(f"Error connecting to Database:\n{e}")
            return None
        
    def execute(self, query: str, params=None, fetch=False, fetchone=False):
        conn = self.get_connection() 
        
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")

        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                result = None
                if fetch and fetchone:
                    raise ValueError("Cannot fetch and fetchone at the same time.")
                if fetchone:
                    result = cur.fetchone()
                elif fetch:
                    result = cur.fetchall()
                
                conn.commit()
                return result
            
        except Error as e:
            print(f"Error in exection:\n{e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self):
        conn = self.get_connection()

        if conn is None:
            raise ConnectionError("Failed to connect to Database.")

        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS gyms (
                        gym_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                        name varchar NOT NULL,
                        location varchar NOT NULL,
                        owner varchar NOT NULL,
                        reputation_score integer DEFAULT 75 CHECK (reputation_score >= 0 AND reputation_score <= 100),
                        UNIQUE(name, location)
                    );
                """)
        
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS fighters (
                        fighter_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                        name varchar NOT NULL,
                        nickname varchar,
                        weight_class varchar NOT NULL CHECK (weight_class IN ('Strawweight', 'Flyweight', 'Bantamweight', 'Featherweight', 
                        'Lightweight', 'Welterweight', 'Middleweight', 'Light Heavyweight', 'Heavyweight', 'Catchweight')),
                        height numeric(5, 2) CHECK (height > 0),
                        age integer NOT NULL CHECK (age > 0),
                        nationality varchar,
                        status varchar DEFAULT 'active' CHECK (status IN ('active', 'retired', 'suspended')),
                        gym_id integer REFERENCES gyms(gym_id) ON DELETE SET NULL
                    );
                """)
                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS trainers (
                        trainer_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                        name varchar NOT NULL,
                        specialty varchar NOT NULL,
                        gym_id integer REFERENCES gyms(gym_id) ON DELETE SET NULL
                    );
                """)

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS fighter_trainer (
                        ft_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                        fighter_id integer REFERENCES fighters(fighter_id) ON DELETE CASCADE,
                        trainer_id integer REFERENCES trainers(trainer_id) ON DELETE CASCADE,
                        start_date date NOT NULL DEFAULT CURRENT_DATE,
                        end_date date CHECK (end_date IS NULL OR end_date >= start_date),
                        UNIQUE NULLS NOT DISTINCT (fighter_id, trainer_id, end_date)
                    );
                """)

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS match_events (
                        match_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                        start_date timestamp NOT NULL,
                        end_date timestamp CHECK (end_date IS NULL OR end_date >= start_date),
                        duration interval GENERATED ALWAYS AS (end_date - start_date) STORED,
                        location varchar NOT NULL
                    );
                """)

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS participants (
                        match_id integer REFERENCES match_events(match_id) ON DELETE CASCADE,
                        fighter_id integer REFERENCES fighters(fighter_id) ON DELETE CASCADE,
                        result varchar CHECK (result IN ('win', 'loss', 'draw', 'no contest')),
                        PRIMARY KEY (match_id, fighter_id)
                    );
                """)

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS fighter_records (
                        fighter_id integer PRIMARY KEY REFERENCES fighters(fighter_id) ON DELETE CASCADE,
                        wins integer DEFAULT 0 CHECK (wins >= 0),
                        losses integer DEFAULT 0 CHECK (losses >= 0),
                        draws integer DEFAULT 0 CHECK (draws >= 0)
                    );
                """)

                conn.commit()
                print("Database schema initialized successfully.")

        except Error as e:
            print(f"Error initializing database:\n{e}")
            conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    # region ==================== Get All Items ====================

    def get_all_gyms(self, limit=100):
        conn = self.get_connection()
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")

        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT gym_id, name, location, owner, reputation_score
                    FROM gyms
                    ORDER BY gym_id DESC
                    LIMIT %s        
                """, (limit,))

                return cur.fetchall()
            
        except Error as e:
            print(f"Error fetching information:\n{e}")
            return None
        finally:
            conn.close()

    def get_all_fighters(self, limit=100):
        conn = self.get_connection()
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT fighter_id, name, nickname, weight_class, height, age, nationality, status, gym_id
                    FROM fighters
                    ORDER BY fighter_id DESC
                    LIMIT %s
                """, (limit,))

                return cur.fetchall()

        except Error as e:
            print(f"Error fetching information:\n{e}")
            return None
        finally:
            conn.close()

    def get_all_trainers(self):
        conn = self.get_connection()
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT trainer_id, name, specialty, gym_id
                    FROM trainers
                    ORDER BY trainer_id
                """)

                return cur.fetchall()

        except Error as e:
            print(f"Error fetching information:\n{e}")
            return None
        finally:
            conn.close()

    def get_all_matches(self):
        conn = self.get_connection()
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT match_id, start_date, end_date, duration, location
                    FROM match_events
                    ORDER BY match_id
                """)

                return cur.fetchall()

        except Error as e:
            print(f"Error fetching information:\n{e}")
            return None
        finally:
            conn.close()

    # endregion

    def get_gym(self, field="gym_id", value=1):
        conn = self.get_connection()
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")
        
        valid_fields = ["gym_id", "name", "location", "owner", "reputation_score"]
        if field not in valid_fields:
            raise ValueError(f"Invalid field name: {field}")

        try:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT gym_id, name, location, owner, reputation_score
                    FROM gyms
                    WHERE {field} = %s
                """, (value,))

                return cur.fetchone()

        except Error as e:
            print(f"Error fetching information:\n{e}")
            return None
        finally:
            conn.close()

    def search_gyms(self, query, limit=100):
        conn = self.get_connection()
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")
        
        try:
            with conn.cursor() as cur:
                query = f"%{query}%"
                cur.execute("""
                    SELECT gym_id, name, location, owner, reputation_score
                    FROM gyms
                    WHERE name ILIKE %s OR location ILIKE %s OR owner ILIKE %s
                    ORDER BY gym_id DESC
                    LIMIT %s
                """, (query, query, query, limit))

                return cur.fetchall()

        except Error as e:
            print(f"Error fetching information:\n{e}")
            return None
        finally:
            conn.close()

    def get_gym_by_reputation(self, min_score=0, max_score=100):
        conn = self.get_connection()
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT gym_id, name, location, owner, reputation_score
                    FROM gyms
                    WHERE reputation_score BETWEEN %s AND %s
                    ORDER BY reputation_score DESC
                """, (min_score, max_score))

                return cur.fetchall()

        except Error as e:
            print(f"Error fetching information:\n{e}")
            return None
        finally:
            conn.close()

    # region ====================== Add Items ======================

    def create_gym(self, name, location, owner, reputation_score=75):
        conn = self.get_connection()
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO gyms (name, location, owner, reputation_score)
                    VALUES (%s, %s, %s, %s)
                    RETURNING gym_id
                """, (name, location, owner, reputation_score))

                gym_id = cur.fetchone()[0] # type: ignore
                conn.commit()
                return gym_id

        except Error as e:
            print(f"Error writing information:\n{e}")
            conn.rollback()
            return None
        finally:
            conn.close()

    def update_gym(self, gym_id, field, value):
        conn = self.get_connection()
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")
        
        valid_fields = ['name', 'location', 'owner', 'reputation_score']
        if field not in valid_fields:
            raise ValueError(f"Invalid field name: {field}")

        try:
            with conn.cursor() as cur:
                cur.execute(f"""
                    UPDATE gyms
                    SET {field} = %s
                    WHERE gym_id = %s
                """, (value, gym_id))

                conn.commit()
                return True

        except Error as e:
            print(f"Error updating information:\n{e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def delete_gym(self, gym_id):
        conn = self.get_connection()
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM gyms
                    WHERE gym_id = %s
                """, (gym_id,))

                conn.commit()
                return True

        except Error as e:
            print(f"Error deleting information:\n{e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def create_fighter(self, name, nickname, weight_class, height, age, nationality, status, gym_id):
        conn = self.get_connection()
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO fighters (name, nickname, weight_class, height, age, nationality, status, gym_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING fighter_id
                """, (name, nickname, weight_class, height, age, nationality, status, gym_id))

                fighter_id = cur.fetchone()[0] # type: ignore

                cur.execute("""
                    INSERT INTO fighter_records (fighter_id, wins, losses, draws)
                    VALUES (%s, 0, 0, 0)
                """, (fighter_id,))

                conn.commit()
                return fighter_id

        except Error as e:
            print(f"Error writing information:\n{e}")
            conn.rollback()
            return None
        finally:
            conn.close()

    def update_fighter(self, fighter_id, field, value):
        conn = self.get_connection()
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")
        
        valid_fields = ['name', 'nickname', 'weight_class', 'height', 'age', 'nationality', 'status', 'gym_id']
        if field not in valid_fields:
            raise ValueError(f"Invalid field name: {field}")

        try:
            with conn.cursor() as cur:
                cur.execute(f"""
                    UPDATE fighters
                    SET {field} = %s
                    WHERE fighter_id = %s
                """, (value, fighter_id))

                conn.commit()
                return True

        except Error as e:
            print(f"Error updating information:\n{e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def delete_fighter(self, fighter_id):
        conn = self.get_connection()
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM fighters
                    WHERE fighter_id = %s
                """, (fighter_id,))

                conn.commit()
                return True

        except Error as e:
            print(f"Error deleting information:\n{e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def create_trainer(self, name, specialty, gym_id):
        conn = self.get_connection()
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO trainers (name, specialty, gym_id)
                    VALUES (%s, %s, %s)
                    RETURNING trainer_id
                """, (name, specialty, gym_id))

                trainer_id = cur.fetchone()[0] # type: ignore
                conn.commit()
                return trainer_id

        except Error as e:
            print(f"Error writing information:\n{e}")
            conn.rollback()
            return None
        finally:
            conn.close()

    def update_trainer(self, trainer_id, field, value):
        conn = self.get_connection()
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")
        
        valid_fields = ['name', 'specialty', 'gym_id']
        if field not in valid_fields:
            raise ValueError(f"Invalid field name: {field}")

        try:
            with conn.cursor() as cur:
                cur.execute(f"""
                    UPDATE trainers
                    SET {field} = %s
                    WHERE trainer_id = %s
                """, (value, trainer_id))

                conn.commit()
                return True

        except Error as e:
            print(f"Error updating information:\n{e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def delete_trainer(self, trainer_id):
        conn = self.get_connection()
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM trainers
                    WHERE trainer_id = %s
                """, (trainer_id,))

                conn.commit()
                return True

        except Error as e:
            print(f"Error deleting information:\n{e}")
            conn.rollback()
            return False
        finally:
            conn.close()




    def get_gym_fighters(self, gym_id):
        conn = self.get_connection()
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT fighter_id, name, nickname, weight_class, height, age, nationality, status, gym_id
                    FROM fighters
                    WHERE gym_id = %s
                """, (gym_id,))

                return cur.fetchall()

        except Error as e:
            print(f"Error fetching information:\n{e}")
            return None
        finally:
            conn.close()

    def get_gym_trainers(self, gym_id):
        conn = self.get_connection()
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT trainer_id, name, specialty, gym_id
                    FROM trainers
                    WHERE gym_id = %s
                """, (gym_id,))

                return cur.fetchall()

        except Error as e:
            print(f"Error fetching information:\n{e}")
            return None
        finally:
            conn.close()

    def get_fighter(self, field="fighter_id", value=1):
        conn = self.get_connection()
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")
        
        valid_fields = ['fighter_id', 'name', 'nickname', 'weight_class', 'height', 'age', 'nationality', 'status', 'gym_id']
        if field not in valid_fields:
            raise ValueError(f"Invalid field name: {field}")

        try:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT fighter_id, name, nickname, weight_class, height, age, nationality, status, gym_id
                    FROM fighters
                    WHERE {field} = %s 
                """, (value,))

                return cur.fetchone()

        except Error as e:
            print(f"Error fetching information:\n{e}")
            return None
        finally:
            conn.close()

    def search_fighters(self, query, limit=100):
        conn = self.get_connection()
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")
        
        try:
            with conn.cursor() as cur:
                query = f"%{query}%"
                cur.execute("""
                    SELECT fighter_id, name, nickname, weight_class, height, age, nationality, status, gym_id
                    FROM fighters
                    WHERE name ILIKE %s OR nickname ILIKE %s
                    ORDER BY fighter_id DESC
                    LIMIT %s
                """, (query, query, limit))

                return cur.fetchall()

        except Error as e:
            print(f"Error fetching information:\n{e}")
            return None
        finally:
            conn.close()

    def get_fighter_trainers(self, fighter_id):
        conn = self.get_connection()
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT t.trainer_id, t.name, t.specialty, t.gym_id
                    FROM trainers t
                    LEFT JOIN fighter_trainer ft ON ft.trainer_id = t.trainer_id AND ft.fighter_id = %s
                    ORDER BY t.trainer_id
                """, (fighter_id,))

                return cur.fetchall()

        except Error as e:
            print(f"Error fetching information:\n{e}")
            return None
        finally:
            conn.close()

    def get_trainer(self, field="trainer_id", value=1):
        conn = self.get_connection()
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")
        
        valid_fields = ['trainer_id', 'name', 'specialty', 'gym_id']
        if field not in valid_fields:
            raise ValueError(f"Invalid field name: {field}")
        
        try:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT trainer_id, name, specialty, gym_id
                    FROM trainers
                    WHERE {field} = %s
                """, (value,))

                return cur.fetchone()

        except Error as e:
            print(f"Error fetching information:\n{e}")
            return None
        finally:
            conn.close()

    def search_trainers(self, query, limit=100):
        conn = self.get_connection()
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")
        
        try:
            with conn.cursor() as cur:
                query = f"%{query}%"
                cur.execute("""
                    SELECT trainer_id, name, specialty, gym_id
                    FROM trainers
                    WHERE name ILIKE %s OR specialty ILIKE %s
                    ORDER BY trainer_id DESC
                    LIMIT %s
                """, (query, query, limit))

                return cur.fetchall()

        except Error as e:
            print(f"Error fetching information:\n{e}")
            return None
        finally:
            conn.close()

    def get_trainer_fighters(self, trainer_id):
        conn = self.get_connection()
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT f.fighter_id, f.name, f.nickname, f.weight_class, f.height, f.age, f.nationality, f.status, f.gym_id
                    FROM fighters f
                    LEFT JOIN fighter_trainer ft ON ft.fighter_id = f.fighter_id AND ft.trainer_id = %s
                    ORDER BY f.fighter_id
                """, (trainer_id,))

                return cur.fetchall()

        except Error as e:
            print(f"Error fetching information:\n{e}")
            return None
        finally:
            conn.close()

    def get_match_info(self, match_id):
        conn = self.get_connection()
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        m.match_id,
                        f1.fighter_id as fighter1_id,
                        f1.name as fighter1_name,
                        p1.result as fighter1_result,
                        f2.fighter_id as fighter2_id,
                        f2.name as fighter2_name,
                        p2.result as fighter2_result
                    FROM match_events m
                    JOIN participants p1 ON m.match_id = p1.match_id
                    JOIN participants p2 ON m.match_id = p2.match_id
                    JOIN fighters f1 ON p1.fighter_id = f1.fighter_id
                    JOIN fighters f2 ON p2.fighter_id = f2.fighter_id
                    WHERE m.match_id = %s AND p1.fighter_id < p2.fighter_id
                    LIMIT 1
                """, (match_id,))

                return cur.fetchone()

        except Error as e:
            print(f"Error fetching information:\n{e}")
            return None
        finally:
            conn.close()

    def get_fighter_matches(self, fighter_id):
        conn = self.get_connection()
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT match_id, start_date, end_date, duration, location
                    FROM match_events
                    JOIN participants ON match_events.match_id = participants.match_id
                    WHERE participants.fighter_id = %s
                    ORDER BY match_id
                """, (fighter_id,))

                return cur.fetchall()

        except Error as e:
            print(f"Error fetching information:\n{e}")
            return None
        finally:
            conn.close()

    def create_match(self, start_date, location, fighter1_id, fighter2_id, end_date, winner_id):
        conn = self.get_connection()
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO match_events (start_date, end_date, location)
                    VALUES (%s, %s, %s)
                    RETURNING match_id
                """, (start_date, end_date, location))
                match_id = cur.fetchone()[0] # type: ignore

                fighter1_result = None
                fighter2_result = None

                if winner_id is not None:
                    if winner_id == fighter1_id:
                        fighter1_result = "win"
                        fighter2_result = "loss"
                    elif winner_id == fighter2_id:
                        fighter1_result = "loss"
                        fighter2_result = "win"
                    elif winner_id == 0:
                        fighter1_result = "draw"
                        fighter2_result = "draw"
                    else:
                        fighter1_result = "no contest"
                        fighter2_result = "no contest"

                cur.execute("""
                    INSERT INTO participants (match_id, fighter_id, result)
                    VALUES (%s, %s, %s)
                """, (match_id, fighter1_id, fighter1_result))

                cur.execute("""
                    INSERT INTO participants (match_id, fighter_id, result)
                    VALUES (%s, %s, %s)
                """, (match_id, fighter2_id, fighter2_result))

                if fighter1_result and fighter1_result != "no contest":
                    self.add_fighter_record(conn, fighter1_id, fighter1_result)
                if fighter2_result and fighter2_result != "no contest":
                    self.add_fighter_record(conn, fighter2_id, fighter2_result)

                conn.commit()
                return match_id

        except Error as e:
            print(f"Error writing information:\n{e}")
            conn.rollback()
            return None
        finally:
            conn.close()

    def update_match_player(self, match_id, old_fighter_id, new_fighter_id):
        conn = self.get_connection()
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT result
                    FROM participants
                    WHERE match_id = %s AND fighter_id = %s
                """, (match_id, old_fighter_id))

                result = cur.fetchone()
                result = result[0] if result else None

                if not result:
                    raise ValueError(f"Fighter with ID: {old_fighter_id} did not participate in this match.")

                if result == "win":
                    cur.execute("""
                    UPDATE fighter_records
                    SET wins = wins - 1
                    WHERE fighter_id = %s    
                """, (old_fighter_id))
                elif result == "draw":
                    cur.execute("""
                    UPDATE fighter_records
                    SET draws = draws - 1
                    WHERE fighter_id = %s    
                """, (old_fighter_id))
                elif result == "loss":
                    cur.execute("""
                    UPDATE fighter_records
                    SET losses = losses - 1
                    WHERE fighter_id = %s    
                """, (old_fighter_id))
                    
                self.add_fighter_record(conn, new_fighter_id, result)

                cur.execute("""
                    UPDATE participants
                    SET fighter_id = %s
                    WHERE match_id = %s AND fighter_id = %s
                """, (new_fighter_id, match_id, old_fighter_id))

                conn.commit()
                return True
            
        except Error as e:
            print(f"Error writing information:\n{e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def update_match_result(self, match_id, winner_id):
        conn = self.get_connection()
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT fighter_id 
                    FROM participants 
                    WHERE match_id = %s
                    LIMIT 2
                """, (match_id,))

                fighters = cur.fetchall()
                fighter1_id = cast(dict, fighters[0])["fighter_id"]
                fighter2_id = cast(dict, fighters[1])["fighter_id"]
                
                fighter1_result = None
                fighter2_result = None      
                
                if winner_id == fighter1_id:
                    fighter1_result = "win"
                    fighter2_result = "loss"
                elif winner_id == fighter2_id:
                    fighter1_result = "loss"
                    fighter2_result = "win"
                elif winner_id == 0:
                    fighter1_result = "draw"
                    fighter2_result = "draw"
                else:
                    fighter1_result = "no contest"
                    fighter2_result = "no contest"

                cur.execute("""
                    SELECT result 
                    FROM participants 
                    WHERE match_id = %s AND fighter_id = %s
                """, (match_id, fighter1_id))

                current_fighter1_result = cur.fetchone()
                current_fighter1_result = current_fighter1_result[0] if current_fighter1_result else None
                
                cur.execute("""
                    SELECT result 
                    FROM participants 
                    WHERE match_id = %s AND fighter_id = %s
                """, (match_id, fighter2_id))

                current_fighter2_result = cur.fetchone()
                current_fighter2_result = current_fighter2_result[0] if current_fighter2_result else None
                
                cur.execute("""
                    UPDATE participants
                    SET result = %s
                    WHERE match_id = %s AND fighter_id = %s
                """, (fighter1_result, match_id, fighter1_id))
                
                cur.execute("""
                    UPDATE participants
                    SET result = %s
                    WHERE match_id = %s AND fighter_id = %s
                """, (fighter2_result, match_id, fighter2_id))
                
                if current_fighter1_result in ('win', 'loss', 'draw'):
                    if fighter1_result in ('win', 'loss', 'draw') and fighter1_result != current_fighter1_result:
                        self.update_fighter_record(conn, fighter1_id, fighter1_result, current_fighter1_result)
                
                if current_fighter2_result in ('win', 'loss', 'draw'):
                    if fighter2_result in ('win', 'loss', 'draw') and fighter2_result != current_fighter2_result:
                        self.update_fighter_record(conn, fighter2_id, fighter2_result, current_fighter2_result)

                conn.commit()
                return True

        except Error as e:
            print(f"Error writing information:\n{e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def delete_match(self, match_id):
        conn = self.get_connection()
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT fighter_id, result
                    FROM participants
                    WHERE match_id = %s
                """, (match_id,))

                participants = cur.fetchall()
                for participant in participants:
                    fighter_id = participant["fighter_id"] # type: ignore
                    result = participant["result"] # type: ignore

                    if result == "win":
                        cur.execute(
                            "UPDATE fighter_records SET wins = wins - 1 WHERE fighter_id = %s",
                            (fighter_id,)
                        )
                    elif result == "loss":
                        cur.execute(
                            "UPDATE fighter_records SET losses = losses - 1 WHERE fighter_id = %s",
                            (fighter_id,)
                        )
                    elif result == "draw":
                        cur.execute(
                            "UPDATE fighter_records SET draws = draws - 1 WHERE fighter_id = %s",
                            (fighter_id,)
                        )

                cur.execute("""
                    DELETE FROM match_events
                    WHERE match_id = %s
                """, (match_id,))

                conn.commit()
                return True

        except Error as e:
            print(f"Error deleting information:\n{e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def add_fighter_record(self, conn, fighter_id, result):
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT fighter_id
                    FROM fighter_records
                    WHERE fighter_id = %s
                """, (fighter_id,))

                record = cur.fetchone()
                if record:
                    cur.execute("""
                        UPDATE fighter_records
                        SET wins = wins + %s, losses = losses + %s, draws = draws + %s
                        WHERE fighter_id = %s
                    """, (1 if result == 'win' else 0, 1 if result == 'loss' else 0, 1 if result == 'draw' else 0, fighter_id))
                else:
                    cur.execute("""
                        INSERT INTO fighter_records (fighter_id, wins, losses, draws)
                        VALUES (%s, %s, %s, %s)
                    """, (fighter_id, 1 if result == 'win' else 0, 1 if result == 'loss' else 0, 1 if result == 'draw' else 0))

                return True

        except Error as e:
            print(f"Error writing information:\n{e}")
            conn.rollback()
            return False

    def update_fighter_record(self, conn, fighter_id, result, current_result):
        if conn is None:
            raise ConnectionError("Failed to connect to Database.")
        
        try:
            with conn.cursor() as cur:
                if result == current_result:
                    return True

                if current_result == "win":
                    cur.execute("UPDATE fighter_records SET wins = wins - 1 WHERE fighter_id = %s", (fighter_id,))
                elif current_result == "loss":
                    cur.execute("UPDATE fighter_records SET losses = losses - 1 WHERE fighter_id = %s", (fighter_id,))
                elif current_result == "draw":
                    cur.execute("UPDATE fighter_records SET draws = draws - 1 WHERE fighter_id = %s", (fighter_id,))
                
                # Then, add the new result
                if result == "win":
                    cur.execute("UPDATE fighter_records SET wins = wins + 1 WHERE fighter_id = %s", (fighter_id,))
                elif result == "loss":
                    cur.execute("UPDATE fighter_records SET losses = losses + 1 WHERE fighter_id = %s", (fighter_id,))
                elif result == "draw":
                    cur.execute("UPDATE fighter_records SET draws = draws + 1 WHERE fighter_id = %s", (fighter_id,))

                return True

        except Error as e:
            print(f"Error writing information:\n{e}")
            conn.rollback()
            return False
        
db = Database()