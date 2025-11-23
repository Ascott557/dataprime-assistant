#!/usr/bin/env python3
"""
Copyright (c) 2024 Coralogix Ltd.

Black Friday Traffic Scenario - Realistic E-commerce Traffic Patterns
Implements progressive traffic increase with realistic user journeys.
"""

import time
import random
import requests
from datetime import datetime
import structlog
from opentelemetry import trace

logger = structlog.get_logger()
tracer = trace.get_tracer(__name__)


class BlackFridayScenario:
    """Manages Black Friday traffic generation with progressive load and realistic user behavior."""
    
    def __init__(self):
        # Traffic parameters
        self.normal_rpm = 30       # Normal traffic: 30 requests/minute
        self.peak_rpm = 120        # Peak Black Friday: 120 requests/minute
        self.ramp_duration = 10    # Minutes to ramp from 30→120
        self.peak_duration = 5     # Minutes at peak (10-15)
        self.degradation_start = 15  # Minute when failures begin
        
        # Statistics tracking
        self.requests_sent = 0
        self.errors = 0
        self.checkouts_attempted = 0
        self.checkouts_failed = 0
        self.start_timestamp = None
        
        # User journey definitions
        self.journeys = {
            'browse_only': {
                'weight_normal': 0.60,      # 60% just browse
                'weight_degraded': 0.50,    # 50% during failures (frustration)
                'steps': [
                    ('GET', 'products', {
                        'category': lambda: random.choice(['electronics', 'furniture', 'sports']),
                        'price_min': 0,
                        'price_max': 1000
                    }),
                    ('GET', 'products', {
                        'category': 'electronics',
                        'price_min': 0,
                        'price_max': 2000
                    })
                ]
            },
            'browse_and_cart': {
                'weight_normal': 0.25,      # 25% add to cart
                'weight_degraded': 0.20,    # 20% during failures
                'steps': [
                    ('GET', 'products', {
                        'category': 'sports',
                        'price_min': 0,
                        'price_max': 500
                    }),
                    ('POST', 'cart/add', {
                        'product_id': lambda: random.randint(1, 10),
                        'quantity': lambda: random.randint(1, 3)
                    }),
                    ('GET', 'cart', {})
                ]
            },
            'full_checkout': {
                'weight_normal': 0.15,      # 15% attempt checkout
                'weight_degraded': 0.30,    # 30% during failures (retries!)
                'steps': [
                    ('GET', 'products', {
                        'category': 'electronics',
                        'price_min': 0,
                        'price_max': 2000
                    }),
                    ('POST', 'cart/add', {
                        'product_id': lambda: random.randint(1, 10),
                        'quantity': lambda: random.randint(1, 2)
                    }),
                    ('GET', 'cart', {}),
                    ('POST', 'checkout/create', {
                        'user_id': lambda: f'user-{random.randint(1000, 9999)}',
                        'product_id': lambda: random.randint(1, 10),
                        'quantity': lambda: random.randint(1, 3)
                    })
                ]
            }
        }
    
    def get_current_rpm(self, elapsed_minutes):
        """Calculate RPM based on current phase."""
        if elapsed_minutes < self.ramp_duration:
            # Linear ramp: 30 → 120 RPM
            progress = elapsed_minutes / self.ramp_duration
            return int(self.normal_rpm + (self.peak_rpm - self.normal_rpm) * progress)
        else:
            # Sustained peak
            return self.peak_rpm
    
    def get_current_phase(self, elapsed_minutes):
        """Get current demo phase name."""
        if elapsed_minutes < 10:
            return "ramp"
        elif elapsed_minutes < 15:
            return "peak"
        elif elapsed_minutes < 20:
            return "degradation"
        else:
            return "critical"
    
    def get_journey_distribution(self, elapsed_minutes):
        """Get journey weights based on phase."""
        if elapsed_minutes < self.degradation_start:
            # Normal distribution
            return {
                'browse_only': self.journeys['browse_only']['weight_normal'],
                'browse_and_cart': self.journeys['browse_and_cart']['weight_normal'],
                'full_checkout': self.journeys['full_checkout']['weight_normal']
            }
        else:
            # Degraded: more retries (higher checkout weight)
            return {
                'browse_only': self.journeys['browse_only']['weight_degraded'],
                'browse_and_cart': self.journeys['browse_and_cart']['weight_degraded'],
                'full_checkout': self.journeys['full_checkout']['weight_degraded']
            }
    
    def select_journey(self, elapsed_minutes):
        """Select a journey based on current distribution."""
        distribution = self.get_journey_distribution(elapsed_minutes)
        
        # Weighted random choice
        rand = random.random()
        cumulative = 0
        
        for journey_type, weight in distribution.items():
            cumulative += weight
            if rand <= cumulative:
                return journey_type
        
        # Fallback
        return 'browse_only'
    
    def resolve_param_value(self, value):
        """Resolve parameter value (handle callables)."""
        if callable(value):
            return value()
        return value
    
    def execute_journey(self, journey_type, service_urls, propagate_fn):
        """Execute a user journey with proper tracing."""
        with tracer.start_as_current_span(f"user_journey.{journey_type}") as span:
            span.set_attribute("user.journey", journey_type)
            span.set_attribute("user.session_id", f'session-{random.randint(10000, 99999)}')
            
            journey = self.journeys[journey_type]
            
            for i, step_def in enumerate(journey['steps']):
                method, endpoint, params = step_def
                
                with tracer.start_as_current_span(f"journey_step.{i+1}.{endpoint}") as step_span:
                    step_span.set_attribute("http.method", method)
                    step_span.set_attribute("step.number", i + 1)
                    step_span.set_attribute("step.endpoint", endpoint)
                    
                    # Resolve dynamic parameters
                    resolved_params = {
                        k: self.resolve_param_value(v)
                        for k, v in params.items()
                    }
                    
                    # Build URL
                    if endpoint == 'products':
                        url = f"{service_urls['product_catalog']}/products"
                    elif endpoint == 'cart/add':
                        url = f"{service_urls['cart']}/cart/add"
                    elif endpoint == 'cart':
                        url = f"{service_urls['cart']}/cart"
                    elif endpoint == 'checkout/create':
                        url = f"{service_urls['checkout']}/orders/create"
                    else:
                        logger.warning("unknown_endpoint", endpoint=endpoint)
                        continue
                    
                    # Propagate trace context
                    headers = propagate_fn()
                    
                    try:
                        if method == "GET":
                            response = requests.get(
                                url,
                                params=resolved_params,
                                headers=headers,
                                timeout=10
                            )
                        else:  # POST
                            response = requests.post(
                                url,
                                json=resolved_params,
                                headers=headers,
                                timeout=10
                            )
                        
                        self.requests_sent += 1
                        
                        # Track checkout attempts/failures
                        if 'checkout' in endpoint:
                            self.checkouts_attempted += 1
                            if response.status_code >= 400:
                                self.checkouts_failed += 1
                        
                        if response.status_code >= 400:
                            self.errors += 1
                            step_span.set_attribute("error", True)
                            step_span.set_attribute("http.status_code", response.status_code)
                        else:
                            step_span.set_attribute("http.status_code", response.status_code)
                    
                    except requests.exceptions.Timeout:
                        self.errors += 1
                        if 'checkout' in endpoint:
                            self.checkouts_failed += 1
                        step_span.set_attribute("error", True)
                        step_span.set_attribute("error.type", "timeout")
                        logger.error("journey_step_timeout", step=endpoint)
                    
                    except Exception as e:
                        self.errors += 1
                        if 'checkout' in endpoint:
                            self.checkouts_failed += 1
                        step_span.set_attribute("error", True)
                        step_span.set_attribute("error.message", str(e))
                        logger.error("journey_step_failed", step=endpoint, error=str(e))
                    
                    # Small delay between steps (realistic user behavior)
                    time.sleep(random.uniform(0.5, 2.0))
    
    def generate_traffic(self, duration_minutes, start_timestamp, service_urls, propagate_fn):
        """
        Main traffic generation loop.
        
        Args:
            duration_minutes: Total demo duration
            start_timestamp: Unix timestamp of demo start
            service_urls: Dict with service URLs
            propagate_fn: Function to propagate trace context
        """
        self.start_timestamp = start_timestamp
        end_time = start_timestamp + (duration_minutes * 60)
        
        logger.info(
            "black_friday_traffic_started",
            duration_minutes=duration_minutes,
            start_timestamp=start_timestamp,
            peak_rpm=self.peak_rpm
        )
        
        minute_counter = 0
        
        while time.time() < end_time:
            elapsed_minutes = (time.time() - start_timestamp) / 60
            current_rpm = self.get_current_rpm(elapsed_minutes)
            phase = self.get_current_phase(elapsed_minutes)
            
            # Log phase transitions
            current_minute = int(elapsed_minutes)
            if current_minute > minute_counter:
                minute_counter = current_minute
                logger.info(
                    "demo_progress",
                    minute=current_minute,
                    phase=phase,
                    rpm=current_rpm,
                    requests_sent=self.requests_sent,
                    errors=self.errors,
                    error_rate=self.errors / max(1, self.requests_sent)
                )
            
            # Calculate delay between requests
            delay_seconds = 60.0 / current_rpm
            
            # Select and execute journey
            journey_type = self.select_journey(elapsed_minutes)
            
            try:
                self.execute_journey(journey_type, service_urls, propagate_fn)
            except Exception as e:
                logger.error("journey_execution_failed", journey=journey_type, error=str(e))
            
            # Wait before next request
            time.sleep(delay_seconds)
        
        logger.info(
            "black_friday_traffic_completed",
            total_requests=self.requests_sent,
            total_errors=self.errors,
            checkouts_attempted=self.checkouts_attempted,
            checkouts_failed=self.checkouts_failed,
            final_error_rate=self.errors / max(1, self.requests_sent)
        )

