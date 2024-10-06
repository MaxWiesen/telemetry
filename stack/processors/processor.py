import os
import logging
from time import sleep
import pandas as pd



if os.getenv('IN_DOCKER'):
    from db_handler import DBHandler, DBTarget, get_table_column_specs    # Cheesed import statement using bind mount
    from mqtt_handler import MQTTHandler
else:
    from analysis.sql_utils.db_handler import DBHandler, DBTarget, get_table_column_specs
    from stack.ingest.mqtt_handler import MQTTHandler


class DBProcessor:
    def __init__(self, db_handler: DBHandler=None):
        self.handler = db_handler if db_handler else DBHandler()

    def check_alive(self) -> None:
        logging.info(self.handler.simple_select('''SELECT event_id FROM event WHERE status = 1''', handler=self.handler))

    def sliding_window(self, f, query: str, window_size: int, **kwargs) -> None:
        """
            Args:
                f: function to execute with the result of the query
                query: SQL query to run
                window_size: Maximum # of packets to be collected
        """
        
        
        df = self.handler.simple_select(query, handler=self.handler, return_df=True)
        f(df, **kwargs)
        
        
        

    def track_loop(self, last_packet: int, gate: tuple[tuple[float, float], tuple[float, float]], handler: DBHandler) -> float | None:
        """
        Checks if a circuit loop has happened after a given packet
        Args:
            last_packet: checking after this value
            gate: human-measured gate that represents the starting line
        """
        
        # points: list[tuple[tuple[float, float], int]] = self.handler.simple_select(f"SELECT gps, packet_id FROM dynamics WHERE packet_id >= ${last_packet} ORDER BY packet_id ASC LIMIT 500")
        
        points: list[tuple[str, int]] = self.handler.simple_select(f"SELECT d.gps, p.time FROM dynamics d JOIN packet p ON p.packet_id = d.packet_id WHERE d.packet_id >= {last_packet} ORDER BY d.packet_id ASC LIMIT 500", handler=handler, target=DBTarget.LOCAL)
        
        parsed_points: list[tuple[tuple[float, float], int]] = []
        
        for point in points:
            gps_str: str = point[0]
            parsed_points.append((tuple(map(int, gps_str[1:-1].split(', ')))), point[1])
    
        for i in range(len(points) - 1):
            if(self.__is_intersection(gate, [parsed_points[i][0], parsed_points[i + 1][0]])):
                return (parsed_points[i][1] + parsed_points[i + 1][1]) / 2
            
            
        
    def __is_intersection(self, line1: tuple[tuple[float, float], tuple[float, float]], line2: tuple[tuple[float, float], tuple[float, float]]) -> bool:
        """
        Check if a line intersects with another line segment 
        """

        # Calculate the denominator of the intersection formula
        denominator = (line1[0][1] - line1[1][1]) * (line2[0][0] - line2[1][0]) - (line1[0][0] - line1[1][0]) * (line2[0][1] - line2[1][1])

        # If the denominator is zero, the lines are parallel
        if denominator == 0:
            return False  # Parallel lines

        # Calculate t and u
        t = ((line1[0][1] - line2[0][1]) * (line2[0][0] - line2[1][0]) - (line1[0][0] - line2[0][0]) * (line2[0][1] - line2[1][1])) / denominator
        u = ((line1[0][1] - line2[0][1]) * (line1[0][0] - line1[1][0]) - (line1[0][0] - line2[0][0]) * (line1[0][1] - line1[1][1])) / denominator

        # Check if t and u are between 0 and 1 (i.e., the intersection occurs within the segments)
        return 0 <= t <= 1 and 0 <= u <= 1
        
        
        
        
def main():
    # with MQTTHandler(name="terence_dev", host_ip='localhost') as mqtt:
        
        # initialize db handler
    
    processor = DBProcessor()
    
    gate = [[30.2672, -97.7431], [30.2673, -97.7432]]
    
    handler = DBHandler()
    
    while True:
        # last_packet: int = DBHandler.simple_select("SELECT packet_id FROM packet ORDER BY packet_id DESC LIMIT 1", target=DBTarget.LOCAL, handler=handler)[0] 
        last_packet = 0
        sleep(5)
        loop = processor.track_loop(last_packet=last_packet, gate=gate, handler=handler)
        if(loop):
            print(loop)
            
    while True:
        processor.check_alive()
        sleep(5)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()