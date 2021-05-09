import React, { useState, useEffect, useRef } from 'react';
import ReactDOM from 'react-dom';
import './index.css';

const App = () => {
  // NOTE:
  // List is rendered in a table in the browser.
  const [list, setList] = useState([]);
  const [error, setError] = useState(null);

  // NOTE:
  // My idea is to keep the data up to date by comparing two timestamps.
  // serverUpdated is obtained using fetch('/api/updated')
  // Whenever serverUpdated -- timestamp when data was last updated on the server
  // is later than localUpdated -- timestamp when data in this app was last updated
  // we reload `list` using fetch('/api/list').
  // 
  // Using intervals with hooks remain a mystery to me. That's why
  // I borrowed code for the `useInterval` function. 

  // Time stamp of the latest update time on the server
  const [serverUpdated, setServerUpdated] = useState("");
  // Time stamp of the latest update on localhost
  const [localUpdated, setLocalUpdated] = useState("")

  // BEGIN: `useInterval` function def
  // `useInterval` function definition copied and pasted from:
  // https://overreacted.io/making-setinterval-declarative-with-react-hooks/ 
  function useInterval(callback, delay) {
    const savedCallback = useRef();

    // Remember the latest callback.
    useEffect(() => {
      savedCallback.current = callback;
    }, [callback]);
  
    // Set up the interval.
    useEffect(() => {
      function tick() {
        savedCallback.current();
      }
      if (delay !== null) {
        let id = setInterval(tick, delay);
        return () => clearInterval(id);
      }
    }, [delay]);
  }
  // END: `useInterval` def

  let fetchServerUpdated = () => {
    fetch("/api/updated").then(res => res.json()).then(
        (result) => {
          setServerUpdated(new Date(result.timestamp))
        }, (error) => {
          setError(error);
        }
      )
  }

  let fetchList = () => {
    fetch("/api/list").then(res => res.json()
    ).then(
      (result) => {
        setList(result);
      }, (error) => {
        setError(error);
      }
    )
  }

  useEffect(
    () => {
      fetchList();
      setLocalUpdated(new Date());
      fetchServerUpdated();
    }, []
  )
  
  // NOTE:
  // I probbaly botched this part by mistakenly repeating the same code as above.
  // The useEffect hook above (lines 69-75) is supposed to run only once to fetch data and serverUpdated timestamp
  // when this component is mounted.
  // It was idiotic to put the same code down there inside the interval loop. My bad. 
  // As a result, /api/list and /api/updated are requested all the time.
  useInterval(
  ()=>{
    fetchList();
    setLocalUpdated((new Date()));
    fetchServerUpdated()

    let timediff = localUpdated - serverUpdated;
    if (timediff < 0) {
      fetchList();
      setLocalUpdated(serverUpdated);
    }
  }, 500
      )

  if (!list) {
    return <div id="main"><h1>There is nothing to buy.</h1></div>
  } else {
    return <div id="main"><h1>Shopping List</h1>
    <table><tbody>
    {list.map(
      row => <tr><td>{row.name}</td><td> {row.count}</td></tr>
    )}</tbody></table>
    </div>
  }
}

ReactDOM.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
  document.getElementById('root')
);