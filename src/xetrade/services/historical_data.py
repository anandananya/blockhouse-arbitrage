# src/xetrade/services/historical_data.py
from __future__ import annotations
import asyncio
import json
import time
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
import logging
import os
import tempfile

from xetrade.models import Pair, OrderBook
from xetrade.exchanges.base import BaseExchange

logger = logging.getLogger(__name__)

@dataclass
class OrderBookSnapshot:
    """Represents a complete L2 order book snapshot for storage."""
    exchange: str
    pair: str
    timestamp_ms: int
    bids: List[Dict[str, float]]  # [{"price": float, "qty": float}, ...]
    asks: List[Dict[str, float]]  # [{"price": float, "qty": float}, ...]
    capture_latency_ms: float
    sequence_number: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return asdict(self)
    
    @classmethod
    def from_orderbook(cls, orderbook: OrderBook, exchange: str, pair: Pair, 
                      capture_latency_ms: float, sequence_number: int) -> "OrderBookSnapshot":
        """Create snapshot from OrderBook model."""
        return cls(
            exchange=exchange,
            pair=pair.human(),
            timestamp_ms=orderbook.ts_ms,
            bids=[{"price": level.price, "qty": level.qty} for level in orderbook.bids],
            asks=[{"price": level.price, "qty": level.qty} for level in orderbook.asks],
            capture_latency_ms=capture_latency_ms,
            sequence_number=sequence_number
        )

class DataStorage:
    """Abstract base class for data storage backends."""
    
    async def store_snapshot(self, snapshot: OrderBookSnapshot) -> bool:
        """Store a single snapshot. Returns success status."""
        raise NotImplementedError
    
    async def store_batch(self, snapshots: List[OrderBookSnapshot]) -> bool:
        """Store multiple snapshots in a batch. Returns success status."""
        raise NotImplementedError
    
    async def close(self):
        """Clean up resources."""
        pass

class LocalFileStorage(DataStorage):
    """Simple local file storage for development/testing."""
    
    def __init__(self, base_path: str = "./data"):
        self.base_path = base_path
        self.current_file = None
        self.file_handle = None
        self.snapshots_in_file = 0
        self.max_snapshots_per_file = 1000  # Rotate files every 1000 snapshots
        
    async def store_snapshot(self, snapshot: OrderBookSnapshot) -> bool:
        """Store snapshot to local JSON file."""
        try:
            # Create directory if it doesn't exist
            import os
            os.makedirs(self.base_path, exist_ok=True)
            
            # Rotate file if needed
            if self.current_file is None or self.snapshots_in_file >= self.max_snapshots_per_file:
                await self._rotate_file()
            
            # Write snapshot as JSON line
            line = json.dumps(snapshot.to_dict()) + "\n"
            self.file_handle.write(line)
            self.file_handle.flush()
            self.snapshots_in_file += 1
            
            return True
        except Exception as e:
            logger.error(f"Failed to store snapshot: {e}")
            return False
    
    async def store_batch(self, snapshots: List[OrderBookSnapshot]) -> bool:
        """Store multiple snapshots."""
        try:
            for snapshot in snapshots:
                success = await self.store_snapshot(snapshot)
                if not success:
                    return False
            return True
        except Exception as e:
            logger.error(f"Failed to store batch: {e}")
            return False
    
    async def _rotate_file(self):
        """Rotate to a new file."""
        if self.file_handle:
            self.file_handle.close()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_file = f"{self.base_path}/orderbook_snapshots_{timestamp}.jsonl"
        self.file_handle = open(self.current_file, "w")
        self.snapshots_in_file = 0
        logger.info(f"Rotated to new file: {self.current_file}")
    
    async def close(self):
        """Close the current file."""
        if self.file_handle:
            self.file_handle.close()

class S3ParquetStorage(DataStorage):
    """AWS S3 storage with Parquet files for efficient storage and querying."""
    
    def __init__(self, bucket_name: str = "xetrade-data", 
                 aws_region: str = "us-east-1", 
                 mock_mode: bool = True):
        self.bucket_name = bucket_name
        self.aws_region = aws_region
        self.mock_mode = mock_mode
        self.buffer: List[OrderBookSnapshot] = []
        self.max_buffer_size = 100  # Flush to S3 every 100 snapshots
        
        if not mock_mode:
            try:
                import boto3
                self.s3_client = boto3.client('s3', region_name=aws_region)
                logger.info(f"Initialized S3 client for bucket: {bucket_name}")
            except ImportError:
                logger.warning("boto3 not available, falling back to mock mode")
                self.mock_mode = True
        
        if self.mock_mode:
            logger.info("Running in MOCK mode - data will be saved locally instead of S3")
            self.mock_base_path = "./data/s3_mock"
            os.makedirs(self.mock_base_path, exist_ok=True)
    
    async def store_snapshot(self, snapshot: OrderBookSnapshot) -> bool:
        """Add snapshot to buffer and flush if needed."""
        try:
            self.buffer.append(snapshot)
            
            if len(self.buffer) >= self.max_buffer_size:
                return await self._flush_buffer()
            
            return True
        except Exception as e:
            logger.error(f"Failed to store snapshot: {e}")
            return False
    
    async def store_batch(self, snapshots: List[OrderBookSnapshot]) -> bool:
        """Store multiple snapshots."""
        try:
            for snapshot in snapshots:
                self.buffer.append(snapshot)
            
            if len(self.buffer) >= self.max_buffer_size:
                return await self._flush_buffer()
            
            return True
        except Exception as e:
            logger.error(f"Failed to store batch: {e}")
            return False
    
    async def _flush_buffer(self) -> bool:
        """Flush buffer to S3 as Parquet file."""
        if not self.buffer:
            return True
        
        try:
            # Convert snapshots to DataFrame format
            data = []
            for snapshot in self.buffer:
                # Flatten the snapshot for Parquet storage
                for bid in snapshot.bids:
                    data.append({
                        'exchange': snapshot.exchange,
                        'pair': snapshot.pair,
                        'timestamp_ms': snapshot.timestamp_ms,
                        'side': 'bid',
                        'price': bid['price'],
                        'quantity': bid['qty'],
                        'capture_latency_ms': snapshot.capture_latency_ms,
                        'sequence_number': snapshot.sequence_number
                    })
                
                for ask in snapshot.asks:
                    data.append({
                        'exchange': snapshot.exchange,
                        'pair': snapshot.pair,
                        'timestamp_ms': snapshot.timestamp_ms,
                        'side': 'ask',
                        'price': ask['price'],
                        'quantity': ask['qty'],
                        'capture_latency_ms': snapshot.capture_latency_ms,
                        'sequence_number': snapshot.sequence_number
                    })
            
            # Create Parquet file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"orderbook_snapshots_{timestamp}.parquet"
            
            if self.mock_mode:
                # Save locally in mock mode
                filepath = os.path.join(self.mock_base_path, filename)
                await self._save_parquet_mock(data, filepath)
                logger.info(f"Mock S3: Saved {len(self.buffer)} snapshots to {filepath}")
            else:
                # Save to actual S3
                await self._save_parquet_s3(data, filename)
                logger.info(f"S3: Uploaded {len(self.buffer)} snapshots to s3://{self.bucket_name}/{filename}")
            
            # Clear buffer
            self.buffer.clear()
            return True
            
        except Exception as e:
            logger.error(f"Failed to flush buffer: {e}")
            return False
    
    async def _save_parquet_mock(self, data: List[Dict], filepath: str):
        """Save Parquet file locally in mock mode."""
        try:
            import pandas as pd
            df = pd.DataFrame(data)
            df.to_parquet(filepath, index=False)
        except ImportError:
            # Fallback to JSON if pandas not available
            with open(filepath.replace('.parquet', '.jsonl'), 'w') as f:
                for row in data:
                    f.write(json.dumps(row) + '\n')
    
    async def _save_parquet_s3(self, data: List[Dict], filename: str):
        """Save Parquet file to S3."""
        try:
            import pandas as pd
            import tempfile
            
            # Create temporary Parquet file
            df = pd.DataFrame(data)
            with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp_file:
                df.to_parquet(tmp_file.name, index=False)
                
                # Upload to S3
                s3_key = f"orderbook_data/{datetime.now().strftime('%Y/%m/%d')}/{filename}"
                self.s3_client.upload_file(tmp_file.name, self.bucket_name, s3_key)
                
                # Clean up temp file
                os.unlink(tmp_file.name)
                
        except ImportError:
            logger.error("pandas not available for Parquet export")
            raise
    
    async def close(self):
        """Flush remaining buffer before closing."""
        if self.buffer:
            await self._flush_buffer()

class HistoricalDataService:
    """Service for capturing and storing historical L2 order book data."""
    
    def __init__(self, exchanges: List[BaseExchange], storage: DataStorage):
        self.exchanges = exchanges
        self.storage = storage
        self.running = False
        self.sequence_counters: Dict[str, int] = {}
        
    async def start_capture(self, pairs: List[Pair], interval_seconds: float = 1.0,
                           max_duration_minutes: Optional[int] = None):
        """
        Start capturing L2 order book data for specified pairs.
        
        Args:
            pairs: List of trading pairs to capture
            interval_seconds: Capture interval in seconds
            max_duration_minutes: Maximum duration to run (None = run indefinitely)
        """
        self.running = True
        start_time = time.time()
        
        logger.info(f"Starting historical data capture for {len(pairs)} pairs")
        logger.info(f"Interval: {interval_seconds}s, Max duration: {max_duration_minutes}min")
        
        try:
            while self.running:
                # Check if we've exceeded max duration
                if max_duration_minutes and (time.time() - start_time) > (max_duration_minutes * 60):
                    logger.info(f"Reached maximum duration of {max_duration_minutes} minutes")
                    break
                
                # Capture snapshots for all pairs on all exchanges
                snapshots = []
                capture_start = time.time()
                
                for exchange in self.exchanges:
                    for pair in pairs:
                        try:
                            # Get L2 order book
                            orderbook = await exchange.get_l2_orderbook(pair, depth=100)
                            
                            # Calculate capture latency
                            capture_latency = (time.time() - capture_start) * 1000
                            
                            # Generate sequence number
                            key = f"{exchange.name}_{pair.human()}"
                            self.sequence_counters[key] = self.sequence_counters.get(key, 0) + 1
                            
                            # Create snapshot
                            snapshot = OrderBookSnapshot.from_orderbook(
                                orderbook, exchange.name, pair, capture_latency, 
                                self.sequence_counters[key]
                            )
                            snapshots.append(snapshot)
                            
                        except Exception as e:
                            logger.error(f"Failed to capture {pair.human()} on {exchange.name}: {e}")
                
                # Store snapshots
                if snapshots:
                    success = await self.storage.store_batch(snapshots)
                    if success:
                        logger.info(f"Stored {len(snapshots)} snapshots")
                    else:
                        logger.error("Failed to store snapshots")
                
                # Wait for next interval
                elapsed = time.time() - capture_start
                if elapsed < interval_seconds:
                    await asyncio.sleep(interval_seconds - elapsed)
                    
        except KeyboardInterrupt:
            logger.info("Capture interrupted by user")
        except Exception as e:
            logger.error(f"Capture error: {e}")
        finally:
            await self.stop_capture()
    
    async def stop_capture(self):
        """Stop the data capture."""
        self.running = False
        await self.storage.close()
        logger.info("Historical data capture stopped")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get capture statistics."""
        return {
            "sequence_counters": self.sequence_counters.copy(),
            "running": self.running
        }

class DataCaptureManager:
    """High-level manager for data capture operations."""
    
    def __init__(self, storage: DataStorage):
        self.storage = storage
        self.services: Dict[str, HistoricalDataService] = {}
    
    async def start_capture_session(self, session_id: str, exchanges: List[BaseExchange], 
                                  pairs: List[Pair], interval_seconds: float = 1.0,
                                  max_duration_minutes: Optional[int] = None):
        """Start a new capture session."""
        if session_id in self.services:
            logger.warning(f"Session {session_id} already exists, stopping previous session")
            await self.stop_capture_session(session_id)
        
        service = HistoricalDataService(exchanges, self.storage)
        self.services[session_id] = service
        
        # Start capture in background
        asyncio.create_task(
            service.start_capture(pairs, interval_seconds, max_duration_minutes)
        )
        
        logger.info(f"Started capture session {session_id}")
        return service
    
    async def stop_capture_session(self, session_id: str):
        """Stop a capture session."""
        if session_id in self.services:
            await self.services[session_id].stop_capture()
            del self.services[session_id]
            logger.info(f"Stopped capture session {session_id}")
    
    async def stop_all_sessions(self):
        """Stop all capture sessions."""
        for session_id in list(self.services.keys()):
            await self.stop_capture_session(session_id)
    
    def get_session_statistics(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific session."""
        if session_id in self.services:
            return self.services[session_id].get_statistics()
        return None 